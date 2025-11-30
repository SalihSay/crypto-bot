import ccxt
import pandas as pd
import requests
import os
import sys
from datetime import datetime, timedelta

# --- HASSAS VERİLER ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- COINLER ---
COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ARB/USDT'
]
# Test için listeyi kısalttım, çalışınca hepsini eklersin.

TIMEFRAMES = ['15m'] # Test için sadece 15m
PIVOT_LEFT = 10 

exchange = ccxt.binance()

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except: pass

def fetch_data(symbol, timeframe, limit=300):
    try:
        # Ekrana yazdırma: Veri çekmeye başlıyorum
        print(f"   -> Veri isteniyor: {symbol}...") 
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['timestamp_tr'] = df['timestamp'] + timedelta(hours=3)
        return df
    except Exception as e:
        print(f"   !!! HATA: {symbol} verisi çekilemedi. Sebebi: {e}")
        return None

def calculate_strategy(df, symbol, tf):
    df['ph_rolling'] = df['high'].shift(1).rolling(window=PIVOT_LEFT).max()
    df['pl_rolling'] = df['low'].shift(1).rolling(window=PIVOT_LEFT).min()
    
    curr = df.iloc[-2] 
    prev = df.iloc[-3]
    
    htf_res = curr['ph_rolling']
    htf_sup = curr['pl_rolling']
    
    # --- DEBUG BASKISI (HER ŞEYİ YAZDIR) ---
    # Bu satır sayesinde botun kör olup olmadığını anlayacağız.
    time_str = curr['timestamp_tr'].strftime('%H:%M')
    print(f"   🔎 DETAY: {symbol} | Mum: {time_str} | Kapanış: {curr['close']} | Direnç: {htf_res}")

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
        print(f"   🔥 SİNYAL TESPİT EDİLDİ: {symbol} {signal}")

    return signal, curr['close'], curr['timestamp_tr']

if __name__ == "__main__":
    print(f"--- TEŞHİS MODU BAŞLADI: {datetime.now().strftime('%H:%M:%S')} (UTC) ---")
    
    for tf in TIMEFRAMES:
        print(f"\n[{tf}] Periyodu Taranıyor:")
        for symbol in COINS:
            df = fetch_data(symbol, tf)
            if df is not None:
                signal, price, candle_time = calculate_strategy(df, symbol, tf)
                
                if signal:
                    msg = f"🚨 SİNYAL: {symbol} {signal} {price}"
                    send_telegram_message(msg)
            else:
                print(f"   !!! {symbol} için DataFrame boş döndü.")
    
    print("\n--- TEŞHİS MODU BİTTİ ---")
