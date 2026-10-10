import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Nifty 200 Support & Resistance", layout="wide")

st.title("📈 Nifty 200 Support & Resistance Analyzer")

# Screenshot pramane 7 Timeframes
TIMEFRAMES = {
    "1 day in 5 minutes intervals": {"period": "1d", "interval": "5m", "resample_4h": False},
    "5 days in 1 hour intervals": {"period": "5d", "interval": "60m", "resample_4h": False},
    "1 month in 4 hours intervals": {"period": "1mo", "interval": "60m", "resample_4h": True},
    "3 months in 1 day intervals": {"period": "3mo", "interval": "1d", "resample_4h": False},
    "6 months in 1 day intervals": {"period": "6mo", "interval": "1d", "resample_4h": False},
    "1 year in 1 day intervals": {"period": "1y", "interval": "1d", "resample_4h": False},
    "5 years in 1 week intervals": {"period": "5y", "interval": "1wk", "resample_4h": False}
}

# Stock select karnyasaathi list (Nifty 200 mukhya stocks + custom input)
default_stocks = [
    "KOTAKBANK.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", 
    "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "INDIGO.NS"
]

selected_stock = st.selectbox("Stock निवडा किंवा टाईप करा:", default_stocks, index=0)

def fetch_data(symbol, config):
    try:
        # 1. Purna data aadhi download hoto
        data = yf.download(symbol, period=config["period"], interval=config["interval"], progress=False)
        
        if data is None or data.empty or len(data) < 3:
            return None
        
        # 2. MultiIndex clean karne (NameError taalnasaathi)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        # 3. 4H Candle banvane
        if config["resample_4h"]:
            data = data.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
        return data
    except Exception:
        return None

def get_levels(data):
    # Previous Candle nusar Pivot calculate karto
    h = float(data['High'].iloc[-2] if len(data) > 1 else data['High'].iloc[-1])
    l = float(data['Low'].iloc[-2] if len(data) > 1 else data['Low'].iloc[-1])
    c = float(data['Close'].iloc[-2] if len(data) > 1 else data['Close'].iloc[-1])
    ltp = float(data['Close'].iloc[-1])
    
    pivot = (h + l + c) / 3.0
    r1 = (2.0 * pivot) - l
    s1 = (2.0 * pivot) - h
    r2 = pivot + (h - l)
    s2 = pivot - (h - l)
    
    lookback = min(20, len(data))
    swing_r = float(data['High'].tail(lookback).max())
    swing_s = float(data['Low'].tail(lookback).min())
    
    return {
        "LTP": round(ltp, 2),
        "Pivot": round(pivot, 2),
        "Support 1": round(s1, 2),
        "Resistance 1": round(r1, 2),
        "Support 2": round(s2, 2),
        "Resistance 2": round(r2, 2),
        "Swing Support": round(swing_s, 2),
        "Swing Resistance": round(swing_r, 2)
    }

if st.button("Calculate Levels", type="primary"):
    with st.spinner(f"{selected_stock} चे सर्व टाइमफ्रेम्स अ‍ॅनालाइज होत आहेत..."):
        results = {}
        for tf_name, cfg in TIMEFRAMES.items():
            stock_df = fetch_data(selected_stock, cfg)
            if stock_df is not None and not stock_df.empty:
                results[tf_name] = get_levels(stock_df)
                
        if results:
            df_final = pd.DataFrame(results).T
            st.success(f"{selected_stock} चे Support आणि Resistance लेव्हल्स:")
            st.dataframe(df_final, use_container_width=True)
        else:
            st.error("डेटा लोड करण्यात अडचण आली. कृपया पुन्हा प्रयत्न करा.")
