import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import os
import sys

# --- HASSAS VERİLERİ GITHUB SECRET'TAN ALACAGIZ ---
# Kodun içine token yazmak güvenlik açığıdır.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

COINS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT', 
         'TRX/USDT', 'AVAX/USDT', 'XRP/USDT', 'AAVE/USDT']
TIMEFRAME = '15m'
PIVOT_LEFT = 10

exchange = ccxt.binance()

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram ayarları eksik!")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
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
    # Pivot Hesapla
    df['ph_rolling'] = df['high'].shift(1).rolling(window=PIVOT_LEFT).max()
    df['pl_rolling'] = df['low'].shift(1).rolling(window=PIVOT_LEFT).min()
    
    # Son kapanmış mumu analiz et (Action anlık veriyle değil, kapanışla çalışır)
    # GitHub Actions bazen 1-2 dk gecikmeli çalışabilir, son kapanmış muma bakmak garantidir.
    curr = df.iloc[-2] # Son tamamlanmış mum
    prev = df.iloc[-3] # Ondan önceki mum
    
    htf_res = curr['ph_rolling']
    htf_sup = curr['pl_rolling']
    
    # SFP
    raw_bear = (curr['high'] > htf_res) and (curr['close'] < htf_res)
    raw_bull = (curr['low'] < htf_sup) and (curr['close'] > htf_sup)
    
    # Engulfing
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
    print("Tarama Başladı...")
    signals_found = False
    
    for symbol in COINS:
        df = fetch_data(symbol, TIMEFRAME)
        if df is not None:
            signal, price = calculate_strategy(df)
            if signal:
                msg = f"🚨 **SİNYAL** 🚨\n\nCoin: {symbol}\nYön: {signal}\nFiyat: {price}\nPeriyot: {TIMEFRAME}"
                print(msg)
                send_telegram_message(msg)
                signals_found = True
    
    if not signals_found:
        print("Sinyal bulunamadı.")
