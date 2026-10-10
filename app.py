import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# Page setup
st.set_page_config(page_title="Supply & Demand Zone Scanner", layout="wide")

st.title("🎯 Strong Supply & Demand Zone Scanner")
st.caption("७-८%+ शार्प मूव्ह आणि स्टीप अँगलवर आधारित प्रेडिक्टिव्ह सप्लाय व डिमांड झोन")

# Sidebar Controls
st.sidebar.header("कंट्रोल्स व पॅरामीटर्स")

ticker = st.sidebar.text_input("स्टॉक टिकर (NSE साठी .NS लावा)", value="BAJFINANCE.NS")
timeframe = st.sidebar.selectbox("टाइमफ्रेम (Timeframe)", ["1d", "1h"], index=0)
period = st.sidebar.selectbox("डेटा पिरियड", ["6mo", "1y", "2y"], index=1)

is_index = "NIFTY" in ticker.upper() or "^" in ticker

default_threshold = 4.0 if is_index else 7.0
min_move_pct = st.sidebar.slider(
    "किमान हालचाल मर्यादा (% Move Threshold)", 
    min_value=3.0, 
    max_value=20.0, 
    value=float(default_threshold), 
    step=0.5
)

max_bars = st.sidebar.slider(
    "कमाल कँडल्स (तीव्रतेसाठी / Sharp Move Bars)", 
    min_value=2, 
    max_value=12, 
    value=5, 
    help="कमी कँडल्समध्ये मोठी मुव्ह आल्यास अँगल २५ अंशांपेक्षा तीव्र मानला जातो."
)

@st.cache_data(ttl=3600)
def fetch_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    return df

df = fetch_data(ticker, period, timeframe)

if df.empty:
    st.error("डेटा लोड करता आला नाही. कृपया टिकर तपासा.")
    st.stop()

# ----------------------------------------------------
# Logic: Strong Demand & Supply Zones Detection
# ----------------------------------------------------
def identify_zones(data, move_threshold, max_allowed_bars):
    detected_zones = []
    n = len(data)

    for i in range(1, n - max_allowed_bars):
        origin_candle = data.iloc[i]
        
        # Check moves across subsequent bars
        for bar_offset in range(1, max_allowed_bars + 1):
            target_idx = i + bar_offset
            if target_idx >= n:
                break
            
            target_candle = data.iloc[target_idx]
            
            # --- 1. Supply Zone (Sharp Fall / Drop) ---
            pct_fall = ((origin_candle['High'] - target_candle['Low']) / origin_candle['High']) * 100
            if pct_fall >= move_threshold:
                # 50% Body / Zone of origin candle
                candle_mid = (origin_candle['Open'] + origin_candle['Close']) / 2
                zone_top = origin_candle['High']
                zone_bottom = candle_mid
                
                detected_zones.append({
                    "type": "Supply",
                    "origin_date": data.index[i],
                    "target_date": data.index[target_idx],
                    "zone_top": zone_top,
                    "zone_bottom": zone_bottom,
                    "pct_move": pct_fall,
                    "bars": bar_offset
                })
                break  # Origin zone captured, move to next candle
                
            # --- 2. Demand Zone (Sharp Rally / Advance) ---
            pct_rise = ((target_candle['High'] - origin_candle['Low']) / origin_candle['Low']) * 100
            if pct_rise >= move_threshold:
                candle_mid = (origin_candle['Open'] + origin_candle['Close']) / 2
                zone_top = candle_mid
                zone_bottom = origin_candle['Low']
                
                detected_zones.append({
                    "type": "Demand",
                    "origin_date": data.index[i],
                    "target_date": data.index[target_idx],
                    "zone_top": zone_top,
                    "zone_bottom": zone_bottom,
                    "pct_move": pct_rise,
                    "bars": bar_offset
                })
                break

    return detected_zones

zones = identify_zones(df, min_move_pct, max_bars)

# ----------------------------------------------------
# Chart Plotting
# ----------------------------------------------------
fig = go.Figure()

# Candlestick chart
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='Price'
))

# Draw zones on chart
last_date = df.index[-1]

for zone in zones:
    color = "rgba(239, 83, 80, 0.25)" if zone['type'] == "Supply" else "rgba(38, 166, 154, 0.25)"
    border_color = "red" if zone['type'] == "Supply" else "green"

    # Zone rectangle
    fig.add_shape(
        type="rect",
        x0=zone['origin_date'],
        y0=zone['zone_bottom'],
        x1=last_date,
        y1=zone['zone_top'],
        fillcolor=color,
        line=dict(color=border_color, width=1, dash="dot"),
    )

fig.update_layout(
    title=f"{ticker} — Supply & Demand Zones",
    yaxis_title="Price (₹)",
    xaxis_title="Date",
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
    height=650
)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------
# Identified Zones Summary Table
# ----------------------------------------------------
st.subheader("शोधलेले झोन्स (Detected Zones Summary)")

if zones:
    table_data = []
    for z in zones:
        table_data.append({
            "प्रकार (Type)": z['type'],
            "तारीख (Date)": z['origin_date'].strftime('%Y-%m-%d'),
            "झोन रेंज (₹)": f"{z['zone_bottom']:.2f} - {z['zone_top']:.2f}",
            "हालचाल (Move %)": f"{z['pct_move']:.2f}%",
            "कँडल्स संख्या (Bars)": z['bars']
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)
else:
    st.info("दिलेल्या अटींनुसार कोणताही झोन सापडला नाही. साइडबारमधील पॅरामीटर्स थोडे बदलून पहा.")
