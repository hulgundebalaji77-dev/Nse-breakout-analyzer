import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Nifty 200 Price Match Scanner", layout="wide")
st.title("🎯 Nifty 200 Price Match: Exact Support & Resistance")

# ----------------- 1. Nifty 200 Stock List -----------------
@st.cache_data(ttl=86400)
def load_nifty200():
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        df = pd.read_csv(url, storage_options=headers)
        return df[['Symbol', 'Company Name']]
    except Exception:
        fallback = {
            "Symbol": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "TATAMOTORS", "SBIN", "ITC", "LT", "AXISBANK"],
            "Company Name": ["Reliance", "TCS", "HDFC Bank", "Infosys", "ICICI Bank", "Tata Motors", "SBI", "ITC", "L&T", "Axis Bank"]
        }
        return pd.DataFrame(fallback)

n200_df = load_nifty200()

# ----------------- 2. Sidebar Settings -----------------
st.sidebar.header("🎯 Price Matching Settings")

TIMEFRAME_MAP = {
    "15 मिनिटे (Intraday)": {"interval": "15m", "period": "5d"},
    "1 तास (Short Term)": {"interval": "60m", "period": "1mo"},
    "1 दिवस (Daily Swing)": {"interval": "1d", "period": "6mo"},
    "1 आठवडा (Positional)": {"interval": "1wk", "period": "1y"}
}

tf_choice = st.sidebar.selectbox("टाइमफ्रेम (Timeframe):", list(TIMEFRAME_MAP.keys()), index=2)
interval = TIMEFRAME_MAP[tf_choice]["interval"]
period = TIMEFRAME_MAP[tf_choice]["period"]

match_type = st.sidebar.radio(
    "Price Matching Mode:",
    ["Exact Level Match (कॅन्डलने लेव्हल टेस्ट केली आहे)", "Tight Proximity (% Match)"]
)

# जर % Match निवडला तरच टॉलरन्स स्लाइडर दाखवणे
if match_type == "Tight Proximity (% Match)":
    match_tolerance = st.sidebar.slider("Tolerance (% मॅच अंतर):", min_value=0.05, max_value=0.50, value=0.15, step=0.05)
else:
    match_tolerance = 0.05  # अगदी नगण्य फरक (Exact साठी)

swing_window = st.sidebar.slider("Swing Lookback Candles:", min_value=10, max_value=40, value=15)
scan_button = st.sidebar.button("🚀 Match Scan सुरू करा")

# ----------------- 3. Price Match Logic -----------------
def scan_and_match(symbol_list, interval, period, window, tol, mode):
    matched_results = []
    tickers = [f"{s}.NS" for s in symbol_list]

    raw_data = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        group_by='ticker',
        threads=True,
        progress=False
    )

    for sym in symbol_list:
        ticker = f"{sym}.NS"
        try:
            if ticker not in raw_data.columns.levels[0]:
                continue
            df = raw_data[ticker].dropna()
            if len(df) < window + 2:
                continue

            curr_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]

            curr_close = curr_candle['Close']
            curr_high = curr_candle['High']
            curr_low = curr_candle['Low']

            # Pivot Points (मागील पूर्ण कॅन्डलवरून)
            p_high, p_low, p_close = prev_candle['High'], prev_candle['Low'], prev_candle['Close']
            pivot = (p_high + p_low + p_close) / 3
            r1 = (2 * pivot) - p_low
            s1 = (2 * pivot) - p_high

            # Swing Levels
            swing_res = df['High'].iloc[-window:-1].max()
            swing_sup = df['Low'].iloc[-window:-1].min()

            levels = {
                "Swing Support": swing_sup,
                "Support 1 (S1)": s1,
                "Swing Resistance": swing_res,
                "Resistance 1 (R1)": r1
            }

            for level_name, level_price in levels.items():
                is_matched = False
                match_status = ""
                diff_pct = abs(curr_close - level_price) / level_price * 100

                if "Support" in level_name:
                    if mode.startswith("Exact"):
                        # कॅन्डलने सपोर्ट लेव्हलला खाली स्पर्श केला किंवा टेस्ट केला
                        if curr_low <= level_price <= curr_high or abs(curr_low - level_price) / level_price * 100 <= 0.08:
                            is_matched = True
                            match_status = "🟢 Support Tested / Exact Hit"
                    else:
                        # Close प्राईस सपोर्टच्या अगदी जवळ मॅच झाली आहे
                        if diff_pct <= tol:
                            is_matched = True
                            match_status = f"🟢 Near Support ({diff_pct:.2f}%)"

                elif "Resistance" in level_name:
                    if mode.startswith("Exact"):
                        # कॅन्डलने रेझिस्टन्स लेव्हलला वर स्पर्श केला किंवा टेस्ट केला
                        if curr_low <= level_price <= curr_high or abs(curr_high - level_price) / level_price * 100 <= 0.08:
                            is_matched = True
                            match_status = "🔴 Resistance Tested / Exact Hit"
                    else:
                        # Close प्राईस रेझिस्टन्सच्या अगदी जवळ मॅच झाली आहे
                        if diff_pct <= tol:
                            is_matched = True
                            match_status = f"🔴 Near Resistance ({diff_pct:.2f}%)"

                if is_matched:
                    matched_results.append({
                        "Symbol": sym,
                        "LTP (₹)": round(curr_close, 2),
                        "Matched Level": level_name,
                        "Level Price (₹)": round(level_price, 2),
                        "फरक (₹)": round(curr_close - level_price, 2),
                        "फरक (%)": round(diff_pct, 2),
                        "Status": match_status,
                        "S1": round(s1, 2),
                        "R1": round(r1, 2),
                        "Swing Low": round(swing_sup, 2),
                        "Swing High": round(swing_res, 2)
                    })
                    break  # एका शेअरसाठी एक प्रमुख मॅच सापडल्यास पुरेसे आहे
        except Exception:
            continue

    return pd.DataFrame(matched_results)

# ----------------- 4. Results & Display -----------------
if scan_button or 'match_data' not in st.session_state:
    with st.spinner("Nifty 200 शेअर्समध्ये Price Matching सुरू आहे..."):
        match_df = scan_and_match(
            n200_df['Symbol'].tolist(),
            interval,
            period,
            swing_window,
            match_tolerance,
            match_type
        )
        st.session_state['match_data'] = match_df
        st.session_state['matched_tf'] = tf_choice

match_df = st.session_state.get('match_data', pd.DataFrame())

if not match_df.empty:
    st.success(f"🎯 अचूक मॅच झालेले शेअर्स: {len(match_df)} (Timeframe: {st.session_state.get('matched_tf')})")
    
    st.dataframe(
        match_df.sort_values(by="फरक (%)")[["Symbol", "LTP (₹)", "Status", "Matched Level", "Level Price (₹)", "फरक (₹)", "फरक (%)"]],
        use_container_width=True
    )

    # ----------------- 5. Chart -----------------
    st.markdown("---")
    st.subheader("📊 Price Match तपासण्यासाठी चार्ट")
    selected_stock = st.selectbox("शेअर निवडा:", match_df["Symbol"].unique())

    if selected_stock:
        chart_df = yf.download(f"{selected_stock}.NS", period=period, interval=interval, progress=False)
        row = match_df[match_df["Symbol"] == selected_stock].iloc[0]

        fig = go.Figure(data=[go.Candlestick(
            x=chart_df.index,
            open=chart_df['Open'],
            high=chart_df['High'],
            low=chart_df['Low'],
            close=chart_df['Close'],
            name="किंमत"
        )])

        # मॅच झालेली लेव्हल ठळक पिवळ्या रंगात दाखवणे
        fig.add_hline(
            y=row['Level Price (₹)'], 
            line_dash="solid", 
            line_color="gold", 
            line_width=2.5,
            annotation_text=f"MATCHED: {row['Matched Level']} (₹{row['Level Price (₹)']})"
        )

        fig.add_hline(y=row['R1'], line_dash="dash", line_color="crimson", annotation_text="R1")
        fig.add_hline(y=row['S1'], line_dash="dash", line_color="mediumseagreen", annotation_text="S1")

        fig.update_layout(
            title=f"{selected_stock} - {row['Matched Level']} वर अचूक प्राईस मॅच",
            yaxis_title="किंमत (₹)",
            xaxis_rangeslider_visible=False,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("दिलेल्या निकषांवर नेमकी प्राईस मॅच सापडली नाही. तुम्ही Tolerance (%) वाढवू शकता किंवा दुसरा Timeframe निवडून स्कॅन करू शकता.")
