{
  "metadata": {
    "kernelspec": {
      "name": "python",
      "display_name": "Python (Pyodide)",
      "language": "python"
    },
    "language_info": {
      "codemirror_mode": {
        "name": "python",
        "version": 3
      },
      "file_extension": ".py",
      "mimetype": "text/x-python",
      "name": "python",
      "nbconvert_exporter": "python",
      "pygments_lexer": "ipython3",
      "version": "3.8"
    }
  },
  "nbformat_minor": 5,
  "nbformat": 4,
  "cells": [
    {
      "id": "0e5c8e9a-6e83-4160-9f58-0299219e213b",
      "cell_type": "code",
      "source": "import ccxt\nimport pandas as pd\nimport pandas_ta as ta\nimport requests\nimport os\nimport sys\n\n# --- HASSAS VERİLERİ GITHUB SECRET'TAN ALACAGIZ ---\n# Kodun içine token yazmak güvenlik açığıdır.\nTELEGRAM_TOKEN = os.environ.get(\"7707501409:AAHxONX9_SUc23lQUkEcQR4vZjs-iKjlYOU\")\nTELEGRAM_CHAT_ID = os.environ.get(\"735859243\")\n\nCOINS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT', \n         'TRX/USDT', 'AVAX/USDT', 'XRP/USDT', 'AAVE/USDT']\nTIMEFRAME = '15m'\nPIVOT_LEFT = 10\n\nexchange = ccxt.binance()\n\ndef send_telegram_message(message):\n    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:\n        print(\"Telegram ayarları eksik!\")\n        return\n    try:\n        url = f\"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage\"\n        data = {\"chat_id\": TELEGRAM_CHAT_ID, \"text\": message}\n        requests.post(url, data=data)\n    except Exception as e:\n        print(f\"Telegram Hatası: {e}\")\n\ndef fetch_data(symbol, timeframe, limit=50):\n    try:\n        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)\n        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])\n        return df\n    except:\n        return None\n\ndef calculate_strategy(df):\n    # Pivot Hesapla\n    df['ph_rolling'] = df['high'].shift(1).rolling(window=PIVOT_LEFT).max()\n    df['pl_rolling'] = df['low'].shift(1).rolling(window=PIVOT_LEFT).min()\n    \n    # Son kapanmış mumu analiz et (Action anlık veriyle değil, kapanışla çalışır)\n    # GitHub Actions bazen 1-2 dk gecikmeli çalışabilir, son kapanmış muma bakmak garantidir.\n    curr = df.iloc[-2] # Son tamamlanmış mum\n    prev = df.iloc[-3] # Ondan önceki mum\n    \n    htf_res = curr['ph_rolling']\n    htf_sup = curr['pl_rolling']\n    \n    # SFP\n    raw_bear = (curr['high'] > htf_res) and (curr['close'] < htf_res)\n    raw_bull = (curr['low'] < htf_sup) and (curr['close'] > htf_sup)\n    \n    # Engulfing\n    bear_engulf = (prev['close'] > prev['open']) and (curr['close'] < curr['open']) and \\\n                  (curr['close'] < prev['open']) and (curr['open'] > prev['close'])\n    bull_engulf = (prev['close'] < prev['open']) and (curr['close'] > curr['open']) and \\\n                  (curr['close'] > prev['open']) and (curr['open'] < prev['close'])\n    \n    signal = None\n    if raw_bull and bull_engulf:\n        signal = \"AL (LONG) 🟢\"\n    elif raw_bear and bear_engulf:\n        signal = \"SAT (SHORT) 🔴\"\n        \n    return signal, curr['close']\n\n# --- ANA ÇALIŞTIRMA BLOĞU ---\nif __name__ == \"__main__\":\n    print(\"Tarama Başladı...\")\n    signals_found = False\n    \n    for symbol in COINS:\n        df = fetch_data(symbol, TIMEFRAME)\n        if df is not None:\n            signal, price = calculate_strategy(df)\n            if signal:\n                msg = f\"🚨 **SİNYAL** 🚨\\n\\nCoin: {symbol}\\nYön: {signal}\\nFiyat: {price}\\nPeriyot: {TIMEFRAME}\"\n                print(msg)\n                send_telegram_message(msg)\n                signals_found = True\n    \n    if not signals_found:\n        print(\"Sinyal bulunamadı.\")",
      "metadata": {
        "trusted": true
      },
      "outputs": [],
      "execution_count": null
    },
    {
      "id": "222f48bf-9d01-4347-9954-8d21eea09f40",
      "cell_type": "code",
      "source": "",
      "metadata": {
        "trusted": true
      },
      "outputs": [],
      "execution_count": null
    }
  ]
}