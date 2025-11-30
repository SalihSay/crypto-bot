import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import os
import sys
from datetime import datetime

# --- HASSAS VERİLER GITHUB SECRET'TAN ALINIYOR ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- TARANACAK COINLER (Toplam 18 Parite) ---
COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT', 
    'TRX/USDT', 'AVAX/USDT', 'XRP/USDT', 'AAVE/USDT',
    'TAO/USDT', 'ZEN/USDT', 'ETC/USDT', 'XMR/USDT', 'DOT/USDT', 
    'ARB/USDT', 'ENA/USDT', 'HYPE/USDT', 'EIGEN/USDT' # HYPE/EIGEN Binance'te listelenmeyebilir, bot atlayacaktır.
]

# --- ZAMAN DİLİMLERİ ---
TIMEFRAMES = ['15m', '1h', '4h'] 
PIVOT_LEFT = 10 # v15.1 Stratejisi

exchange = ccxt.binance()

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram ayarları eksik!")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # Markdown ile kalın metin gönderiliyor
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Hatası: {e}")

def fetch_data(symbol, timeframe, limit=50):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except:
        return None

def calculate_strategy(df):
    # Pivot Hesapla (HTF Direnç/Destek Noktaları)
    df['ph_rolling'] = df['high'].shift(1).rolling(window=PIVOT_LEFT).max()
    df['pl_rolling'] = df['low'].shift(1).rolling(window=PIVOT_LEFT).min()
    
    # Son tamamlanmış mum (curr) ve ondan önceki mum (prev)
    curr = df.iloc[-2] 
    prev = df.iloc[-3]
    
    htf_res = curr['ph_rolling']
    htf_sup = curr['pl_rolling']
    
    # SFP (Likidite Avı)
    raw_bear = (curr['high'] > htf_res) and (curr['close'] < htf_res)
    raw_bull = (curr['low'] < htf_sup) and (curr['close'] > htf_sup)
    
    # Engulfing (Yutan Mum) Onayı
    bear_engulf = (prev['close'] > prev['open']) and (curr['close'] < curr['open']) and \
                  (curr['close'] < prev['open']) and (curr['open'] > prev['close'])
    bull_engulf = (prev['close'] < prev['open']) and (curr['close'] > curr['open']) and \
                  (curr['close'] > prev['open']) and (curr['open'] < prev['close'])
    
    signal = None
    if raw_bull and bull_engulf:
        signal = "AL (LONG) 🟢"
    elif raw_bear and bear_engulf:
        signal = "SAT (SHORT) 🔴"
        
    return signal, curr['close']

# --- ANA ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    start_time = datetime.now()
    print(f"Çoklu Periyot Tarama Başladı: {start_time.strftime('%H:%M:%S')}")
    signals_found = False
    
    # Periyotlar ve Pariteler üzerinde iç içe döngü
    for tf in TIMEFRAMES:
        for symbol in COINS:
            df = fetch_data(symbol, tf)
            
            # Yeterli veri ve başarılı çekim kontrolü
            if df is not None and len(df) > PIVOT_LEFT + 3:
                signal, price = calculate_strategy(df)
                
                if signal:
                    msg = f"🚨 **PA SİNYALİ** 🚨\n\n*Periyot*: **{tf.upper()}**\n*Parite*: **{symbol}**\n*Yön*: **{signal}**\n*Fiyat*: {price:.6f}"
                    print(msg)
                    send_telegram_message(msg)
                    signals_found = True
            elif df is None:
                # Sadece HYPE/EIGEN gibi paritelerde hata mesajını yazdırabiliriz.
                # print(f"Hata: {symbol} için {tf} verisi çekilemedi. (Muhtemelen Binance'te listelenmiyor.)")
                pass

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"Tarama tamamlandı. Süre: {duration:.2f} saniye.")
    
    if not signals_found:
        print("Tarama tamamlandı, yeni sinyal yok.")
