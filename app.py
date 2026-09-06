import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import find_peaks

st.set_page_config(page_title="AI Trend & Breakout Engine", layout="wide")
st.title("🎯 TrendSpider-Style Auto Trendline & Breakout Analyzer")

# Sidebar Controls
st.sidebar.header("⚙️ पॅरामीटर्स आणि सेटिंग्स")
ticker_symbol = st.sidebar.text_input("NSE स्टॉक सिम्बॉल (.NS जोडा):", value="BSE.NS").upper()
time_period = st.sidebar.selectbox("डेटा पिरियड:", ["3mo", "6mo", "1y", "2y"], index=1)
peak_distance = st.sidebar.slider("Swing Peaks Distance (संवेदनशीलता):", min_value=3, max_value=15, value=5)
show_trendlines = st.sidebar.checkbox("Auto Trendlines दाखवा", value=True)
show_sr_zones = st.sidebar.checkbox("Support & Resistance लेव्हल्स दाखवा", value=True)

# 1. डेटा डाउनलोड आणि प्रोसेसिंग
@st.cache_data(ttl=300)
def load_data(ticker, period):
    df = yf.download(ticker, period=period, interval="1d", progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.reset_index(inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    return df

df = load_data(ticker_symbol, time_period)

if df is None or len(df) < 20:
    st.error("डेटा उपलब्ध नाही किंवा सिम्बॉल चुकीचा आहे. कृपया योग्य NSE सिम्बॉल तपासा.")
    st.stop()

# 2. मॅथेमॅटिकल Swing Highs आणि Swing Lows डिटेक्शन (TrendSpider Logic)
high_prices = df['High'].values
low_prices = df['Low'].values

# Peaks (Swing Highs) आणि Troughs (Swing Lows) शोधणे
peaks, _ = find_peaks(high_prices, distance=peak_distance)
troughs, _ = find_peaks(-low_prices, distance=peak_distance)

# 3. मुख्य कँडलस्टिक चार्ट तयार करणे
fig = go.Figure()

# कँडलस्टिक ट्रेस
fig.add_trace(go.Candlestick(
    x=df['Date'],
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name="Price Action"
))

# 4. ऑटोमॅटिक ट्रेंडलाइन (Linear Regression on Recent Swing Highs / Lows)
if show_trendlines:
    # Resistance Trendline (शेवटचे दोन प्रमुख Swing Highs जोडून पुढे नेणे)
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        x_vals = np.array([p1, p2])
        y_vals = np.array([high_prices[p1], high_prices[p2]])
        slope, intercept = np.polyfit(x_vals, y_vals, 1)
        
        extended_x = np.arange(p1, len(df))
        extended_y = slope * extended_x + intercept
        
        fig.add_trace(go.Scatter(
            x=df['Date'].iloc[extended_x],
            y=extended_y,
            mode='lines',
            line=dict(color='rgba(255, 75, 75, 0.9)', width=2, dash='dash'),
            name="Auto Resistance Trendline"
        ))

    # Support Trendline (शेवटचे दोन प्रमुख Swing Lows जोडून पुढे नेणे)
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        x_vals_s = np.array([t1, t2])
        y_vals_s = np.array([low_prices[t1], low_prices[t2]])
        slope_s, intercept_s = np.polyfit(x_vals_s, y_vals_s, 1)
        
        extended_x_s = np.arange(t1, len(df))
        extended_y_s = slope_s * extended_x_s + intercept_s
        
        fig.add_trace(go.Scatter(
            x=df['Date'].iloc[extended_x_s],
            y=extended_y_s,
            mode='lines',
            line=dict(color='rgba(0, 204, 150, 0.9)', width=2, dash='dash'),
            name="Auto Support Trendline"
        ))

# 5. सपोर्ट आणि रेजिस्टन्स झोन्स (Key Horizontal Levels)
latest_close = df['Close'].iloc[-1]
recent_resistance = high_prices[peaks[-1]] if len(peaks) > 0 else df['High'].max()
recent_support = low_prices[troughs[-1]] if len(troughs) > 0 else df['Low'].min()

if show_sr_zones:
    fig.add_hline(y=recent_resistance, line_width=1.5, line_color="#E74C3C", 
                  annotation_text=f"Res: ₹{recent_resistance:.2f}", annotation_position="top right")
    fig.add_hline(y=recent_support, line_width=1.5, line_color="#2ECC71", 
                  annotation_text=f"Sup: ₹{recent_support:.2f}", annotation_position="bottom right")

fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=10, r=10, t=30, b=10),
    template="plotly_dark",
    yaxis_title="किंमत (₹)",
    xaxis_title="तारीख"
)

# 6. डॅशबोर्ड मेट्रिक्स आणि ब्रेकआउट स्थिती
col1, col2, col3, col4 = st.columns(4)

current_vol = df['Volume'].iloc[-1]
avg_vol_20 = df['Volume'].iloc[-21:-1].mean()
vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

is_breakout = latest_close > recent_resistance
is_breakdown = latest_close < recent_support

with col1:
    st.metric("सध्याचा भाव (LTP)", f"₹{latest_close:.2f}")
with col2:
    st.metric("नजीकचा रेजिस्टन्स", f"₹{recent_resistance:.2f}")
with col3:
    st.metric("नजीकचा सपोर्ट", f"₹{recent_support:.2f}")
with col4:
    st.metric("व्हॉल्यूम वाढ (20 MA)", f"{vol_ratio:.2f}x")

# चार्ट रेंडरिंग
st.plotly_chart(fig, use_container_width=True)

# 7. सिस्टिम ॲनालिसिस निष्कर्ष
st.subheader("📋 ऑटो-अनालिसिस सारांश")
if is_breakout:
    if vol_ratio >= 1.5:
        st.success(f"🔥 *Confirmed Breakout:* {ticker_symbol} ने उच्च व्हॉल्यूमसह (Volume Ratio: {vol_ratio:.2f}x) ₹{recent_resistance:.2f} चा रेजिस्टन्स यशस्वीरीत्या ओलांडला आहे.")
    else:
        st.warning(f"⚠️ *Weak Breakout:* रेजिस्टन्स ब्रेक झाला आहे, मात्र व्हॉल्यूम सरासरीपेक्षा कमी आहे. फेक ब्रेकआउटची शक्यता असू शकते.")
elif is_breakdown:
    st.error(f"🔻 *Breakdown Alert:* किंमत ₹{recent_support:.2f} च्या सपोर्ट खाली क्लोज झाली आहे.")
else:
    distance_to_res = ((recent_resistance - latest_close) / latest_close) * 100
    st.info(f"⏳ *Consolidation Mode:* स्टॉक सध्या सपोर्ट (₹{recent_support:.2f}) आणि रेजिस्टन्स (₹{recent_resistance:.2f}) च्या दरम्यान ट्रेड करत आहे. रेजिस्टन्सपासून {distance_to_res:.2f}% अंतरावर आहे.")
