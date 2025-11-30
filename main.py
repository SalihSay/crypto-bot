import ccxt
import pandas as pd
import requests
import os
import sys
from datetime import datetime, timedelta

# --- HASSAS VERİLER ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- COINLER (MEXC Uyumlu) ---
COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT', 
    'TRX/USDT', 'AVAX/USDT', 'XRP/USDT', 'AAVE/USDT',
    'TAO/USDT', 'ZEN/USDT', 'ETC/USDT', 'XMR/USDT', 'DOT/USDT', 
    'ARB/USDT', 'ENA/USDT'
    # HYPE ve EIGEN, MEXC'de listeli değilse hata verebilir, bot bunları atlar.
]

TIMEFRAMES = ['15m', '1h', '4h'] 
PIVOT_LEFT = 10 

# --- KRİTİK DEĞİŞİKLİK: BINANCE YERİNE MEXC KULLANIYORUZ ---
# GitHub (Amerika IP'si) Binance Global'e bağlanamaz ama MEXC'ye bağlanabilir.
exchange = ccxt.mexc() 

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except: pass

def fetch_data(symbol, timeframe, limit=300):
    try:
        # MEXC API'sinden veri çek
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['timestamp_tr'] = df['timestamp'] + timedelta(hours=3)
        return df
    except Exception as e:
        # Hata olursa (örn: O coin MEXC'de yoksa) loga yaz ama programı durdurma
        print(f"Veri Hatası ({symbol}): {e}")
        return None

def calculate_strategy(df, symbol, tf):
    # Pivot Hesapla (Geriye dönük tepe bulucu)
    df['ph_rolling'] = df['high'].shift(1).rolling(window=PIVOT_LEFT).max()
    df['pl_rolling'] = df['low'].shift(1).rolling(window=PIVOT_LEFT).min()
    
    # --- MUM SEÇİMİ ---
    curr = df.iloc[-2] 
    prev = df.iloc[-3]
    
    htf_res = curr['ph_rolling']
    htf_sup = curr['pl_rolling']
    
    # SFP (Likidite Avı)
    raw_bear = (curr['high'] > htf_res) and (curr['close'] < htf_res)
    raw_bull = (curr['low'] < htf_sup) and (curr['close'] > htf_sup)
    
    # Engulfing (Yutan Mum)
    bear_engulf = (prev['close'] > prev['open']) and (curr['close'] < curr['open']) and \
                  (curr['close'] < prev['open']) and (curr['open'] > prev['close'])
    bull_engulf = (prev['close'] < prev['open']) and (curr['close'] > curr['open']) and \
                  (curr['close'] > prev['open']) and (curr['open'] < prev['close'])
    
    signal = None
    if raw_bull and bull_engulf:
        signal = "AL (LONG) 🟢"
    elif raw_bear and bear_engulf:
        signal = "SAT (SHORT) 🔴"
    
    # --- DEBUG LOGU ---
    # Logların çalıştığını görmek için burayı açık tutuyoruz
    if "BTC" in symbol or "ETH" in symbol:
        time_str = curr['timestamp_tr'].strftime('%H:%M')
        print(f"DEBUG [{symbol} {tf}]: Mum={time_str} | Kapanış={curr['close']} | Direnç={htf_res}")

    return signal, curr['close'], curr['timestamp_tr']

# --- ANA ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    print(f"Tarama Başladı (MEXC): {datetime.now().strftime('%H:%M:%S')} (UTC)")
    signals_found = False
    
    for tf in TIMEFRAMES:
        for symbol in COINS:
            df = fetch_data(symbol, tf)
            # Yeterli veri varsa stratejiyi çalıştır
            if df is not None and len(df) > PIVOT_LEFT + 5:
                signal, price, candle_time = calculate_strategy(df, symbol, tf)
                
                if signal:
                    time_str = candle_time.strftime('%d-%m %H:%M')
                    msg = f"🚨 **SİNYAL** 🚨\n\n*Parite*: **{symbol}** (MEXC)\n*Periyot*: {tf}\n*İşlem*: **{signal}**\n*Fiyat*: {price}\n*Mum*: {time_str}"
                    print(msg) 
                    send_telegram_message(msg)
                    signals_found = True
            
            # API Limitlerine takılmamak için minik bekleme (Opsiyonel)
            # time.sleep(0.1) 
    
    if not signals_found:
        print("Sinyal yok.")
