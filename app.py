import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="NSE 200 S&R Candlestick Screener", layout="wide")

st.title("📊 NSE 200 Last High/Low Breakout Screener")
st.caption("Last Candle High (Resistance) & Low (Support) Breakout Detection with Candlestick Charts")

# NSE 200 मधील प्रमुख स्टॉक्सची यादी
NIFTY_200_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", "ITC.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "ADANIENT.NS", "TATAMOTORS.NS", "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS",
    "NTPC.NS", "AXISBANK.NS", "DMART.NS", "POWERGRID.NS", "M&M.NS",
    "ADANIPORTS.NS", "COALINDIA.NS", "BAJAJFINSV.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "IOC.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "SIEMENS.NS", "GRASIM.NS",
    "BEL.NS", "HAL.NS", "VEDL.NS", "PIDILITIND.NS", "BPCL.NS",
    "DLF.NS", "INDIGO.NS", "EICHERMOT.NS", "TRENT.NS", "ZOMATO.NS"
]

# --- साइडबार पर्याय ---
st.sidebar.header("⚙️ Timeframe & Settings")

timeframe_map = {
    "15 Minutes (Intraday)": {"interval": "15m", "period": "5d"},
    "1 Hour (Swing)": {"interval": "60m", "period": "1mo"},
    "1 Day (Daily)": {"interval": "1d", "period": "6mo"},
    "1 Week (Positional)": {"interval": "1wk", "period": "2y"}
}

selected_tf = st.sidebar.selectbox("Select Timeframe:", list(timeframe_map.keys()), index=2)
tf_cfg = timeframe_map[selected_tf]

# --- डेटा अ‍ॅनालिसिस फंक्शन ---
def analyze_stock(ticker, interval, period):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty or len(df) < 5:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # मागील पूर्ण झालेली कँडल (-2) आणि चालू कँडल (-1)
        prev_candle = df.iloc[-2]
        curr_candle = df.iloc[-1]

        last_high = float(prev_candle['High'])   # Resistance
        last_low = float(prev_candle['Low'])     # Support
        current_ltp = float(curr_candle['Close'])
        current_open = float(curr_candle['Open'])

        status = "Inside Range"
        if current_ltp > last_high:
            status = "🚀 Last High Breakout"
        elif current_ltp < last_low:
            status = "🔻 Last Low Breakdown"

        pct_change = ((current_ltp - float(prev_candle['Close'])) / float(prev_candle['Close'])) * 100

        return {
            "Symbol": ticker.replace(".NS", ""),
            "Ticker": ticker,
            "LTP (₹)": round(current_ltp, 2),
            "Change (%)": round(pct_change, 2),
            "Last High (Resistance)": round(last_high, 2),
            "Last Low (Support)": round(last_low, 2),
            "Status": status
        }
    except Exception:
        return None

# --- स्कॅनर चालवणे ---
if st.button(f"🔍 Scan Last Candle High/Low on {selected_tf}"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, sym in enumerate(NIFTY_200_TICKERS):
        status_text.text(f"Analyzing {sym} ({idx+1}/{len(NIFTY_200_TICKERS)})...")
        res = analyze_stock(sym, tf_cfg["interval"], tf_cfg["period"])
        if res:
            results.append(res)
        progress_bar.progress((idx + 1) / len(NIFTY_200_TICKERS))

    status_text.empty()
    progress_bar.empty()

    if results:
        st.session_state["scan_results"] = pd.DataFrame(results)
    else:
        st.warning("डेटा मिळाला नाही.")

# निकाल दाखवणे
if "scan_results" in st.session_state:
    df_res = st.session_state["scan_results"]

    breakouts = df_res[df_res['Status'] == "🚀 Last High Breakout"]
    breakdowns = df_res[df_res['Status'] == "🔻 Last Low Breakdown"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Last High Breakouts", len(breakouts))
    c2.metric("Last Low Breakdowns", len(breakdowns))
    c3.metric("Inside Previous Candle", len(df_res) - len(breakouts) - len(breakdowns))

    st.subheader("📋 फिल्टर झालेली यादी")
    actionable = df_res[df_res['Status'] != "Inside Range"]
    
    if not actionable.empty:
        st.dataframe(actionable.drop(columns=["Ticker"]), use_container_width=True)
    else:
        st.info("या टाइमफ्रेमवर मागील कँडलचा हाय किंवा लो तोडलेला शेअर सापडला नाही.")

    # --- Candlestick Chart सेक्शन ---
    st.markdown("---")
    st.subheader("🕯️ Live Candlestick Chart View")
    
    symbols_list = df_res["Symbol"].tolist()
    selected_stock = st.selectbox("कँडलस्टिक चार्ट पाहण्यासाठी शेअर निवडा:", symbols_list)

    if selected_stock:
        full_ticker = f"{selected_stock}.NS"
        df_chart = yf.download(full_ticker, period=tf_cfg["period"], interval=tf_cfg["interval"], progress=False)
        
        if isinstance(df_chart.columns, pd.MultiIndex):
            df_chart.columns = df_chart.columns.get_level_values(0)

        # शेवटच्या 30 कँडल्स
        df_plot = df_chart.tail(30)
        
        last_high_val = float(df_plot['High'].iloc[-2])
        last_low_val = float(df_plot['Low'].iloc[-2])

        # Plotly Candlestick Chart
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df_plot.index,
            open=df_plot['Open'],
            high=df_plot['High'],
            low=df_plot['Low'],
            close=df_plot['Close'],
            name=selected_stock
        ))

        # Resistance Line
