import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import os
import sys
from datetime import datetime, timedelta

# --- AYARLAR ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

COINS = ['XRP/USDT', 'BTC/USDT', 'ETH/USDT'] # Test için sadece 3 coin yeterli
TIMEFRAME = '15m'
PIVOT_LEFT = 10 

exchange = ccxt.binance()

def fetch_data(symbol, timeframe, limit=300):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: return None

def diagnose_strategy(df, symbol):
    # Pivot Hesapla
    df['ph_rolling'] = df['high'].shift(1).rolling(window=PIVOT_LEFT).max()
    df['pl_rolling'] = df['low'].shift(1).rolling(window=PIVOT_LEFT).min()
    
    # Kapanmış son mumu al (iloc[-2])
    curr = df.iloc[-2]
    prev = df.iloc[-3]
    
    # Zamanı Türkiye Saatine Çevir (Rahat okuman için)
    tr_time = curr['timestamp'] + timedelta(hours=3)
    time_str = tr_time.strftime('%H:%M')
    
    # Değerler
    close_price = curr['close']
    high_price = curr['high']
    res_price = curr['ph_rolling'] # Botun gördüğü direnç
    
    # SFP Koşulu Kontrolü
    # Bearish SFP: High > Direnç VE Close < Direnç
    is_high_above = high_price > res_price
    is_close_below = close_price < res_price
    is_sfp = is_high_above and is_close_below
    
    print(f"🔍 ANALİZ: {symbol} | Mum: {time_str}")
    print(f"   📉 Fiyat: {close_price} | Yüksek: {high_price}")
    print(f"   🧱 Botun Gördüğü Direnç: {res_price}")
    print(f"   🧐 İğne Attı mı? {'EVET' if is_high_above else 'HAYIR'} | Altında Kaldı mı? {'EVET' if is_close_below else 'HAYIR'}")
    print(f"   🚨 SFP Sinyali Var mı? {'VAR 🔴' if is_sfp else 'YOK'}")
    print("-" * 40)

# --- ANA BLOK ---
if __name__ == "__main__":
    print(f"--- DETAYLI TEŞHİS BAŞLADI ({datetime.now().strftime('%H:%M:%S')} UTC) ---\n")
    for symbol in COINS:
        df = fetch_data(symbol, TIMEFRAME)
        if df is not None:
            diagnose_strategy(df, symbol)
