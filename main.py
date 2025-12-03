import ccxt
import pandas as pd
import numpy as np
import requests
import os
import sys
from datetime import datetime, timedelta

# --- HASSAS VERİLER ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- COINLER ---
COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT', 
    'TRX/USDT', 'AVAX/USDT', 'XRP/USDT', 'AAVE/USDT',
    'TAO/USDT', 'ZEN/USDT', 'ETC/USDT', 'AAVE/USDT', 'DOT/USDT', 
    'ARB/USDT', 'ENA/USDT','EIGEN/USDT'
]

TIMEFRAMES = ['1h', '4h'] 
PIVOT_LEFT = 10 
PIVOT_RIGHT = 10

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
        # Pivot algoritması için daha fazla geçmiş veriye ihtiyaç var
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['timestamp_tr'] = df['timestamp'] + timedelta(hours=3)
        return df
    except: return None

# --- YENİ ALGORİTMA: TRADINGVIEW PIVOT SİMÜLASYONU ---
def calculate_pivots(df, left, right):
    """
    TradingView'in pivothigh/pivotlow fonksiyonunun Python karşılığı.
    Bir mumun pivot olması için solundaki 'left' ve sağındaki 'right' kadar mumdan
    daha yüksek/alçak olması gerekir.
    """
    df['is_pivot_high'] = df['high'].rolling(window=left+right+1, center=True).max() == df['high']
    df['is_pivot_low'] = df['low'].rolling(window=left+right+1, center=True).min() == df['low']
    
    # Pivot değerlerini belirle (NaN olmayanlar pivot noktalarıdır)
    # Ancak Pivot oluşumu 'right' kadar bar sonra kesinleşir. Biz geçmiş pivotları arıyoruz.
    
    # Pivot değerlerini bir sütuna yaz
    df['pivot_high_val'] = df.apply(lambda row: row['high'] if row['is_pivot_high'] else None, axis=1)
    df['pivot_low_val'] = df.apply(lambda row: row['low'] if row['is_pivot_low'] else None, axis=1)
    
    # "ValueWhen" Mantığı: Son geçerli pivotu ileri taşı (Fill Forward)
    # Shift(right) yapıyoruz çünkü pivotun teyit edilmesi için sağdaki mumların kapanması lazım.
    # Yani o anki mumda, ancak 10 mum önceki pivotu "kesinleşmiş" olarak görebiliriz.
    df['htf_res'] = df['pivot_high_val'].shift(right).ffill()
    df['htf_sup'] = df['pivot_low_val'].shift(right).ffill()
    
    return df

def calculate_strategy(df, symbol, tf):
    # Yeni Pivot Algoritmasını Çalıştır
    df = calculate_pivots(df, PIVOT_LEFT, PIVOT_RIGHT)
    
    curr = df.iloc[-2] 
    prev = df.iloc[-3]
    
    # Artık "Rolling Max" değil, gerçek "Pivot Direnci"ne bakıyoruz
    htf_res = curr['htf_res']
    htf_sup = curr['htf_sup']
    
    # Eğer veri yetersizliğinden pivot hesaplanamadıysa çık
    if pd.isna(htf_res) or pd.isna(htf_sup):
        return None, None, None

    # --- SFP ---
    raw_bear = (curr['high'] > htf_res) and (curr['close'] < htf_res)
    raw_bull = (curr['low'] < htf_sup) and (curr['close'] > htf_sup)
    
    # --- ENGULFING (>= Düzeltmesi Dahil) ---
    bear_engulf = (prev['close'] > prev['open']) and (curr['close'] < curr['open']) and \
                  (curr['close'] < prev['open']) and (curr['open'] >= prev['close']) 
    bull_engulf = (prev['close'] < prev['open']) and (curr['close'] > curr['open']) and \
                  (curr['close'] > prev['open']) and (curr['open'] <= prev['close'])
    
    signal = None
    if raw_bull and bull_engulf:
        signal = "AL (LONG) 🟢"
    elif raw_bear and bear_engulf:
        signal = "SAT (SHORT) 🔴"
    
    # --- DEBUG LOGU ---
    target_debug = ["SOL", "BTC", "ETH", "XRP"]
    if any(coin in symbol for coin in target_debug):
        time_str = curr['timestamp_tr'].strftime('%H:%M')
        # Artık "Fractal Pivot" değerini göreceksin
        debug_msg = f"DEBUG [{symbol} {tf}]: Mum={time_str} | Close={curr['close']} | PIVOT_RES={htf_res} | SFP?={raw_bear} | Engulf?={bear_engulf}"
        print(debug_msg)

    return signal, curr['close'], curr['timestamp_tr']

if __name__ == "__main__":
    print(f"Tarama Başladı (v18.0 - TV Pivot Fix): {datetime.now().strftime('%H:%M:%S')} (UTC)")
    signals_found = False
    
    for tf in TIMEFRAMES:
        for symbol in COINS:
            df = fetch_data(symbol, tf, limit=500) # Pivot için daha çok veri lazım
            if df is not None and len(df) > 50:
                signal, price, candle_time = calculate_strategy(df, symbol, tf)
                
                if signal:
                    time_str = candle_time.strftime('%d-%m %H:%M')
                    msg = f"🚨 **SİNYAL** 🚨\n\n*Parite*: **{symbol}**\n*Periyot*: {tf}\n*İşlem*: **{signal}**\n*Fiyat*: {price}\n*Mum*: {time_str}"
                    print(msg) 
                    send_telegram_message(msg)
                    signals_found = True
            
    if not signals_found:
        print("Sinyal yok.")
