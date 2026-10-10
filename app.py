import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# पेज कॉन्फिगरेशन
st.set_page_config(page_title="NSE सपोर्ट आणि रेझिस्टन्स अ‍ॅनालायझर", layout="wide")

st.title("🎯 निफ्टी २००: मजबूत सपोर्ट आणि रेझिस्टन्स डॅशबोर्ड")

# स्क्रीनशॉटप्रमाणे सर्व ७ टाइमफ्रेम्स
TIMEFRAMES = {
    "1 day in 5 minutes intervals": {"period": "1d", "interval": "5m", "resample_4h": False},
    "5 days in 1 hour intervals": {"period": "5d", "interval": "60m", "resample_4h": False},
    "1 month in 4 hours intervals": {"period": "1mo", "interval": "60m", "resample_4h": True},
    "3 months in 1 day intervals": {"period": "3mo", "interval": "1d", "resample_4h": False},
    "6 months in 1 day intervals": {"period": "6mo", "interval": "1d", "resample_4h": False},
    "1 year in 1 day intervals": {"period": "1y", "interval": "1d", "resample_4h": False},
    "5 years in 1 week intervals": {"period": "5y", "interval": "1wk", "resample_4h": False}
}

# निफ्टी २०० मधील मुख्य स्टॉक्स
STOCKS_LIST = [
    "KOTAKBANK.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", 
    "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", 
    "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TATAMOTORS.NS", "SUNPHARMA.NS",
    "INDIGO.NS", "TITAN.NS", "TATASTEEL.NS", "NTPC.NS", "POWERGRID.NS"
]

col1, col2 = st.columns([2, 1])
with col1:
    selected_stock = st.selectbox("स्टॉक निवडा:", STOCKS_LIST, index=0)
with col2:
    custom_stock = st.text_input("किंवा दुसरा NSE सिम्बॉल टाका (उदा. M&M.NS):")

ticker = custom_stock.strip().upper() if custom_stock.strip() else selected_stock

def get_clean_data(symbol, config):
    """Yahoo Finance वरून सुरक्षितपणे डेटा डाऊनलोड करतो"""
    try:
        df = yf.download(symbol, period=config["period"], interval=config["interval"], progress=False)
        if df is None or df.empty or len(df) < 5:
            return None
        
        # MultiIndex कॉलम्स व्यवस्थित करणे
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # ४ तासांची कॅण्डल तयार करणे
        if config.get("resample_4h", False):
            df = df.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
        return df
    except Exception:
        return None

def calculate_levels(df):
    """पिव्होट आणि स्विंग हाय/लो नुसार लेव्हल्स काढतो"""
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    n = len(df)
    
    ltp = round(float(closes[-1]), 2)
    
    # १. स्टँडर्ड पिव्होट लेव्हल्स
    prev_h = float(highs[-2] if n > 1 else highs[-1])
    prev_l = float(lows[-2] if n > 1 else lows[-1])
    prev_c = float(closes[-2] if n > 1 else closes[-1])
    
    pivot = (prev_h + prev_l + prev_c) / 3.0
    r1 = (2.0 * pivot) - prev_l
    s1 = (2.0 * pivot) - prev_h
    r2 = pivot + (prev_h - prev_l)
    s2 = pivot - (prev_h - prev_l)
    
    # २. फ्रॅक्टल स्विंग लेव्हल्स (प्राइस अ‍ॅक्शन)
    window = 3 if n < 30 else 5
    raw_res = []
    raw_supp = []
    
    for i in range(window, n - window):
        if highs[i] == max(highs[i - window : i + window + 1]):
            raw_res.append(highs[i])
        if lows[i] == min(lows[i - window : i + window + 1]):
            raw_supp.append(lows[i])
            
    valid_res = [r for r in raw_res if r > ltp]
    valid_supp = [s for s in raw_supp if s < ltp]
    
    # सर्वात जवळचा मजबूत आधार आणि अडथळा
    majboot_r = round(float(min(valid_res)), 2) if valid_res else round(float(r1), 2)
    majboot_s = round(float(max(valid_supp)), 2) if valid_supp else round(float(s1), 2)
    
    return {
        "सध्याची किंमत (LTP)": ltp,
        "पिव्होट पॉईंट": round(pivot, 2),
        "मजबूत सपोर्ट": majboot_s,
        "मजबूत रेझिस्टन्स": majboot_r,
        "सपोर्ट १ (S1)": round(s1, 2),
        "रेझिस्टन्स १ (R1)": round(r1, 2),
        "सपोर्ट २ (S2)": round(s2, 2),
        "रेझिस्टन्स २ (R2)": round(r2, 2)
    }

# अ‍ॅनालिसिस सुरू करण्याचे बटण
if st.button("🚀 लेव्हल्स तपासा", type="primary"):
    with st.spinner(f"{ticker} चे सर्व ७ टाइमफ्रेम्स अ‍ॅनालाइज होत आहेत..."):
        all_results = {}
        for tf_label, cfg in TIMEFRAMES.items():
            df_stock = get_clean_data(ticker, cfg)
            if df_stock is not None and not df_stock.empty:
                all_results[tf_label] = calculate_levels(df_stock)
                
        if all_results:
            st.success(f"✅ {ticker} चे सपोर्ट आणि रेझिस्टन्स लेव्हल्स तयार झाले आहेत:")
            res_df = pd.DataFrame(all_results).T
            st.dataframe(res_df, use_container_width=True)
        else:
            st.error("डेटा उपलब्ध होऊ शकला नाही. कृपया स्टॉक सिम्बॉल तपासा.")
