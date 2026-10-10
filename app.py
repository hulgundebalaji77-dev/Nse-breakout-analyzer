import yfinance as yf
import pandas as pd
import numpy as np

# 1. Screenshot nusar exact 7 time frames chi mapping
TIMEFRAMES = {
    "1 day in 5 minutes intervals": {"period": "1d", "interval": "5m"},
    "5 days in 1 hour intervals": {"period": "5d", "interval": "60m"},
    "1 month in 4 hours intervals": {"period": "1mo", "interval": "60m", "resample_4h": True},
    "3 months in 1 day intervals": {"period": "3mo", "interval": "1d"},
    "6 months in 1 day intervals": {"period": "6mo", "interval": "1d"},
    "1 year in 1 day intervals": {"period": "1y", "interval": "1d"},
    "5 years in 1 week intervals": {"period": "5y", "interval": "1wk"}
}

def fetch_and_prepare_data(symbol, tf_config):
    """Yahoo Finance varun data download ani process karto"""
    df = yf.download(symbol, period=tf_config["period"], interval=tf_config["interval"], progress=False)
    
    if df.empty or len(df) < 5:
        return None
    
    # MultiIndex columns aslyas flatten karne
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 4 Hours interval sathi 1 Hour candles resample karne
    if tf_config.get("resample_4h", False):
        df = df.resample('4h').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
    return df

def calculate_support_resistance(df):
    """Classic Pivot Points ani Swing Levels calculate karto"""
    high = df['High'].iloc[-2] if len(df) > 1 else df['High'].iloc[-1]
    low = df['Low'].iloc[-2] if len(df) > 1 else df['Low'].iloc[-1]
    close = df['Close'].iloc[-2] if len(df) > 1 else df['Close'].iloc[-1]
    ltp = df['Close'].iloc[-1]
    
    # Pivot Point Formula
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    
    # Recent Swing High ani Swing Low
    lookback = min(20, len(df))
    swing_res = df['High'].tail(lookback).max()
    swing_supp = df['Low'].tail(lookback).min()
    
    return {
        "LTP": round(float(ltp), 2),
        "Pivot": round(float(pivot), 2),
        "Support 1 (S1)": round(float(s1), 2),
        "Resistance 1 (R1)": round(float(r1), 2),
        "Support 2 (S2)": round(float(s2), 2),
        "Resistance 2 (R2)": round(float(r2), 2),
        "Swing Support": round(float(swing_supp), 2),
        "Swing Resistance": round(float(swing_res), 2)
    }

def scan_stock(symbol):
    """Stock chya sarva timeframes che support & resistance kadhto"""
    results = {}
    for tf_label, tf_config in TIMEFRAMES.items():
        try:
            df = fetch_and_prepare_data(symbol, tf_config)
            if df is not None:
                results[tf_label] = calculate_support_resistance(df)
        except Exception as e:
            continue
    return pd.DataFrame(results).T

# Example: Screenshot pramane KOTAKBANK kivha Nifty 200 stock
stock_ticker = "KOTAKBANK.NS"
print(f"=== Support and Resistance Levels: {stock_ticker} ===")
levels_table = scan_stock(stock_ticker)
print(levels_table)
