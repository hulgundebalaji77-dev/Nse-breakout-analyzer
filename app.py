import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import find_peaks

# Page Settings
st.set_page_config(
    page_title="AI Pre-Breakout Radar",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Attractive Sea Blue CSS Theme
st.markdown("""
<style>
    /* Main Background - green */
    .stApp {
        background: linear-gradient(180deg, #0a192f 0%, #0d2538 50%, #071626 100%) !important;
        color: #e6f1ff;
    }
    
    /* Sidebar Sea Blue Theme */
    section[data-testid="stSidebar"] {
        background-color: #071829 !important;
        border-right: 1px solid #1e3a5f;
    }
    
    /* Pre-Breakout Card (Sea Blue with Glowing Cyan Border) */
    .pre-breakout-card {
        background: linear-gradient(135deg, rgba(10, 42, 74, 0.85), rgba(7, 24, 41, 0.95));
        border: 1.5px solid #00d2ff;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0, 210, 255, 0.15);
    }
    
    /* Live Breakout Card */
    .metric-card {
        background: linear-gradient(135deg, rgba(13, 37, 63, 0.85), rgba(8, 22, 36, 0.95));
        border: 1.5px solid #00f2fe;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.12);
    }

    /* Badges */
    .badge-pre {
        background: linear-gradient(90deg, #00c6ff, #0072ff);
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-live {
        background: linear-gradient(90deg, #10b981, #059669);
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #0072ff 0%, #00c6ff 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0, 198, 255, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>⚡ AI Pre-Breakout Radar</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8892b0; font-size: 1.1rem;'>उद्या ब्रेकआउट होण्याची दाट शक्यता असणारे आणि ताजे ब्रेकआउट झालेले NSE F&O शेअर्स</p>", unsafe_allow_html=True)

# NSE F&O Top Watchlist
FNO_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",
    "BHARTIARTL.NS", "TATAMOTORS.NS", "ITC.NS", "LT.NS", "BSE.NS", "KPITTECH.NS",
    "CUMMINSIND.NS", "HAL.NS", "DIXON.NS", "BEL.NS", "TRENT.NS", "COALINDIA.NS",
    "M&M.NS", "SUNPHARMA.NS", "AXISBANK.NS", "BAJFINANCE.NS", "CHOLAFIN.NS",
    "PERSISTENT.NS", "POLYCAB.NS", "MCX.NS", "NAUKRI.NS", "TATASTEEL.NS", "VOLTAS.NS"
]

# Sidebar
st.sidebar.title("🎛️ स्कॅनर कंट्रोल्स")
scan_universe = st.sidebar.multiselect("स्कॅन करण्यासाठी स्टॉक्स निवडा:", FNO_STOCKS, default=FNO_STOCKS[:15])
proximity_threshold = st.sidebar.slider("रेजिस्टन्स जवळीक मर्यादा (%)", 0.5, 3.0, 1.5, 0.1)
squeeze_lookback = st.sidebar.slider("कन्सोलिडेशन तपासणी दिवस", 5, 15, 7)

# Calculation Engine
def analyze_pre_breakout(df, proximity, squeeze_days):
    if len(df) < 35:
        return None
    
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    volumes = df['Volume'].values

    # Find swing highs using peak detection
    peaks, _ = find_peaks(highs[:-2], distance=4)
    if len(peaks) == 0:
        return None

    res_level = highs[peaks[-1]]
    ltp = closes[-1]
    prev_close = closes[-2]
    pct_change = ((ltp - prev_close) / prev_close) * 100
    
    # Distance to resistance
    dist_to_res = ((res_level - ltp) / ltp) * 100

    # Volume parameters
    avg_vol_20 = volumes[-21:-1].mean()
    curr_vol = volumes[-1]
    vol_ratio = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

    # Consolidation Squeeze Check (NR7 / Range compression)
    recent_ranges = highs[-squeeze_days:] - lows[-squeeze_days:]
    is_squeeze = recent_ranges[-1] < (recent_ranges.mean() * 0.85)

    # Status Detection
    status = "Normal"
    score = 0
    
    # Condition A: Already Broken Out
    if ltp > res_level:
        status = "Live Breakout"
        score = 95 if vol_ratio >= 1.5 else 75
    # Condition B: One-Day Before Breakout (Pre-Breakout Alert)
    elif 0.0 <= dist_to_res <= proximity:
        if is_squeeze or (0.9 <= vol_ratio <= 2.0):
            status = "Pre-Breakout Ready"
            score = 90 if is_squeeze else 80
        else:
            status = "Near Resistance"
            score = 65

    return {
        "LTP": round(ltp, 2),
        "Change %": round(pct_change, 2),
        "Resistance": round(res_level, 2),
        "Distance %": round(dist_to_res, 2),
        "Volume Ratio": round(vol_ratio, 2),
        "Squeeze": "होय (Active)" if is_squeeze else "नाही",
        "Status": status,
        "AI Score": score
    }

# Scan Execution Button
if st.button("🚀 AI प्री-ब्रेकआउट रडार चालवा", use_container_width=True):
    with st.spinner("बाजारातील डेटा स्कॅन होत आहे आणि AI प्रोबेबिलिटी मोजली जात आहे..."):
        all_data = yf.download(scan_universe, period="6mo", interval="1d", group_by="ticker", progress=False)
        
        pre_breakout_list = []
        live_breakout_list = []
        normal_list = []

        for sym in scan_universe:
            try:
                stock_df = all_data[sym].dropna()
                res = analyze_pre_breakout(stock_df, proximity_threshold, squeeze_lookback)
                if not res:
                    continue
                res["Symbol"] = sym
                
                if res["Status"] == "Pre-Breakout Ready":
                    pre_breakout_list.append(res)
                elif res["Status"] == "Live Breakout":
                    live_breakout_list.append(res)
                else:
                    normal_list.append(res)
            except Exception:
                continue

    # Section 1: 1-Day Before Breakout
    st.markdown("<hr style='border: 0.5px solid #1e3a5f;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #00d2ff;'>🔥 १ दिवस आधीचे सिग्नल (उद्या ब्रेकआउट होण्याची शक्यता)</h3>", unsafe_allow_html=True)
    if pre_breakout_list:
        cols = st.columns(3)
        for i, item in enumerate(pre_breakout_list):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="pre-breakout-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #ffffff;">{item['Symbol']}</h3>
                        <span class="badge-pre">AI Score: {item['AI Score']}/100</span>
                    </div>
                    <hr style="border: 0.5px solid #1e3a5f; margin: 10px 0;">
                    <p style="margin: 4px 0; color: #ccd6f6;"><b>LTP:</b> ₹{item['LTP']} ({item['Change %']}%)</p>
                    <p style="margin: 4px 0; color: #ccd6f6;"><b>रेजिस्टन्स:</b> ₹{item['Resistance']}</p>
                    <p style="margin: 4px 0; color: #64ffda;"><b>रेजिस्टन्सपासून अंतर:</b> फक्त {item['Distance %']}%</p>
                    <p style="margin: 4px 0; color: #8892b0;"><b>व्हॉल्यूम:</b> {item['Volume Ratio']}x | <b>Squeeze:</b> {item['Squeeze']}</p>
                    <small style="color: #00c6ff;">💡 उद्या रेजिस्टन्स पार करताच मोठ्या तेजीची शक्यता.</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("सध्या निवडलेल्या निकषांवर प्री-ब्रेकआउट स्टेजमधील कोणताही शेअर सापडला नाही.")

    # Section 2: Live Confirmed Breakouts
    st.markdown("<h3 style='color: #00f2fe; margin-top: 25px;'>🚀 आज ब्रेकआउट झालेले शेअर्स (Live Breakout)</h3>", unsafe_allow_html=True)
    if live_breakout_list:
        cols_live = st.columns(3)
        for i, item in enumerate(live_breakout_list):
            with cols_live[i % 3]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #ffffff;">{item['Symbol']}</h3>
                        <span class="badge-live">Live Breakout</span>
                    </div>
                    <hr style="border: 0.5px solid #1e3a5f; margin: 10px 0;">
                    <p style="margin: 4px 0; color: #ccd6f6;"><b>LTP:</b> ₹{item['LTP']} ({item['Change %']}%)</p>
                    <p style="margin: 4px 0; color: #ccd6f6;"><b>तुटलेला रेजिस्टन्स:</b> ₹{item['Resistance']}</p>
                    <p style="margin: 4px 0; color: #10b981;"><b>व्हॉल्यूम सर्ज:</b> {item['Volume Ratio']}x</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("आज कोणत्याही शेअरने रेजिस्टन्स तोडलेला नाही.")

    # Section 3: Detailed Table
    st.markdown("<hr style='border: 0.5px solid #1e3a5f;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #00d2ff;'>📋 संपूर्ण स्कॅनिंग डेटा टेबल</h3>", unsafe_allow_html=True)
    full_df = pd.DataFrame(pre_breakout_list + live_breakout_list + normal_list)
    if not full_df.empty:
        st.dataframe(full_df[['Symbol', 'LTP', 'Change %', 'Resistance', 'Distance %', 'Volume Ratio', 'Squeeze', 'Status', 'AI Score']], use_container_width=True)

# ----------------- Single Interactive Visualizer -----------------
st.markdown("<hr style='border: 0.5px solid #1e3a5f;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color: #00d2ff;'>🔍 चार्टवर कन्सोलिडेशन आणि लेव्हल्स तपासा</h3>", unsafe_allow_html=True)
chart_stock = st.selectbox("स्टॉक निवडा:", FNO_STOCKS)
chart_df = yf.download(chart_stock, period="6mo", interval="1d", progress=False)

if not chart_df.empty:
    if isinstance(chart_df.columns, pd.MultiIndex):
        chart_df.columns = chart_df.columns.get_level_values(0)
    chart_df.reset_index(inplace=True)

    highs = chart_df['High'].values
    peaks, _ = find_peaks(highs[:-2], distance=4)
    res_val = highs[peaks[-1]] if len(peaks) > 0 else chart_df['High'].max()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=chart_df['Date'], open=chart_df['Open'], high=chart_df['High'],
        low=chart_df['Low'], close=chart_df['Close'], name="Price Action"
    ))
    
    # Resistance Line
    fig.add_hline(y=res_val, line_dash="dash", line_color="#00d2ff", 
                  annotation_text=f"Breakout Trigger Level: ₹{res_val:.2f}", annotation_position="top right")

    # Deep Sea Blue Chart Layout
    fig.update_layout(
        paper_bgcolor="#071829",
        plot_bgcolor="#0a1f36",
        height=480,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(color="#ccd6f6"),
        xaxis=dict(gridcolor="#13314d"),
        yaxis=dict(gridcolor="#13314d")
    )
    st.plotly_chart(fig, use_container_width=True)
