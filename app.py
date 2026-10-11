import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="NSE 200 S&R Screener", layout="wide")

st.title("🕯️ NSE Top 200 - Support & Resistance Candlestick Screener")

# NSE 200 pramukh stocks chi yadi
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

# --- Photo madhe dakhavlele Intervals & Periods ---
TIMEFRAME_OPTIONS = {
    "1 day in 5 minutes intervals": {"period": "1d", "interval": "5m", "resample": None},
    "5 days in 1 hour intervals": {"period": "5d", "interval": "60m", "resample": None},
    "1 month in 4 hours intervals": {"period": "1mo", "interval": "60m", "resample": "4h"},
    "3 months in 1 day intervals": {"period": "3mo", "interval": "1d", "resample": None},
    "6 months in 1 day intervals": {"period": "6mo", "interval": "1d", "resample": None},
    "1 year in 1 day intervals": {"period": "1y", "interval": "1d", "resample": None},
    "5 years in 1 week intervals": {"period": "5y", "interval": "1wk", "resample": None}
}

st.sidebar.header("⚙️ Time Frame Setting")
selected_tf = st.sidebar.radio(
    "Select Timeframe:",
    list(TIMEFRAME_OPTIONS.keys()),
    index=0
)

tf_info = TIMEFRAME_OPTIONS[selected_tf]

# --- Data Fetching & Processing Function ---
def fetch_stock_data(ticker, cfg):
    try:
        df = yf.download(ticker, period=cfg["period"], interval=cfg["interval"], progress=False)
        if df.empty or len(df) < 5:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 4 Hours sathi 1h data resample karne
        if cfg["resample"] == "4h":
            if df.index.tz is not None:
                df.index = df.index.tz_convert('Asia/Kolkata')
            df = df.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        # EMA Indicators (9, 21, 50, 200)
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

        return df
    except Exception:
        return None

# --- S&R Breakout Analysis ---
def check_breakout(ticker, cfg):
    df = fetch_stock_data(ticker, cfg)
    if df is None or len(df) < 3:
        return None

    prev_bar = df.iloc[-2]
    curr_bar = df.iloc[-1]

    last_high = float(prev_bar['High'])
    last_low = float(prev_bar['Low'])
    ltp = float(curr_bar['Close'])

    status = "Inside Range"
    if ltp > last_high:
        status = "🚀 Last High Breakout"
    elif ltp < last_low:
        status = "🔻 Last Low Breakdown"

    pct_chg = ((ltp - float(prev_bar['Close'])) / float(prev_bar['Close'])) * 100

    return {
        "Symbol": ticker.replace(".NS", ""),
        "Ticker": ticker,
        "LTP (₹)": round(ltp, 2),
        "Change (%)": round(pct_chg, 2),
        "Last High (Res)": round(last_high, 2),
        "Last Low (Sup)": round(last_low, 2),
        "Status": status
    }

# --- Scan Button ---
if st.button(f"🔍 Scan Stocks ({selected_tf})"):
    results = []
    prog = st.progress(0)
    msg = st.empty()

    for i, sym in enumerate(NIFTY_200_TICKERS):
        msg.text(f"Scanning {sym} ({i+1}/{len(NIFTY_200_TICKERS)})...")
        res = check_breakout(sym, tf_info)
        if res:
            results.append(res)
        prog.progress((i + 1) / len(NIFTY_200_TICKERS))

    msg.empty()
    prog.empty()

    if results:
        st.session_state["results"] = pd.DataFrame(results)
        st.session_state["chosen_tf"] = selected_tf

# --- Results Display ---
if "results" in st.session_state:
    df_res = st.session_state["results"]
    curr_tf = st.session_state.get("chosen_tf", selected_tf)

    breakouts = df_res[df_res['Status'] == "🚀 Last High Breakout"]
    breakdowns = df_res[df_res['Status'] == "🔻 Last Low Breakdown"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Resistance Breakouts", len(breakouts))
    c2.metric("Support Breakdowns", len(breakdowns))
    c3.metric("Inside Range", len(df_res) - len(breakouts) - len(breakdowns))

    st.subheader(f"📋 Breakout List ({curr_tf})")
    filtered = df_res[df_res['Status'] != "Inside Range"]

    if not filtered.empty:
        st.dataframe(filtered.drop(columns=["Ticker"]), use_container_width=True)
    else:
        st.info("Ya timeframe var sadhya kontahi breakout kiva breakdown bhetla nahi.")

    # --- Candlestick Chart View ---
    st.markdown("---")
    st.subheader("🕯️ Interactive Candlestick Chart with EMAs")

    selected_symbol = st.selectbox("Stock select kara:", df_res["Symbol"].tolist())

    if selected_symbol:
        full_ticker = f"{selected_symbol}.NS"
        df_chart = fetch_stock_data(full_ticker, tf_info)

        if df_chart is not None and not df_chart.empty:
            df_plot = df_chart.tail(50)
            res_val = float(df_plot['High'].iloc[-2])
            sup_val = float(df_plot['Low'].iloc[-2])

            fig = go.Figure()

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df_plot.index.strftime('%Y-%m-%d %H:%M') if 'm' in tf_info["interval"] or tf_info["resample"] else df_plot.index.strftime('%Y-%m-%d'),
                open=df_plot['Open'],
                high=df_plot['High'],
                low=df_plot['Low'],
                close=df_plot['Close'],
                name=selected_symbol
            ))

            # EMA Lines
            fig.add_trace(go.Scatter(x=df_plot.index.strftime('%Y-%m-%d %H:%M') if 'm' in tf_info["interval"] or tf_info["resample"] else df_plot.index.strftime('%Y-%m-%d'), y=df_plot['EMA9'], mode='lines', line=dict(color='yellow', width=1), name='EMA 9'))
            fig.add_trace(go.Scatter(x=df_plot.index.strftime('%Y-%m-%d %H:%M') if 'm' in tf_info["interval"] or tf_info["resample"] else df_plot.index.strftime('%Y-%m-%d'), y=df_plot['EMA21'], mode='lines', line=dict(color='orange', width=1), name='EMA 21'))
            fig.add_trace(go.Scatter(x=df_plot.index.strftime('%Y-%m-%d %H:%M') if 'm' in tf_info["interval"] or tf_info["resample"] else df_plot.index.strftime('%Y-%m-%d'), y=df_plot['EMA50'], mode='lines', line=dict(color='cyan', width=1.2), name='EMA 50'))
            fig.add_trace(go.Scatter(x=df_plot.index.strftime('%Y-%m-%d %H:%M') if 'm' in tf_info["interval"] or tf_info["resample"] else df_plot.index.strftime('%Y-%m-%d'), y=df_plot['EMA200'], mode='lines', line=dict(color='magenta', width=1.5), name='EMA 200'))

            # Last High (Resistance) Line
            fig.add_hline(y=res_val, line_dash="dash", line_color="green", line_width=2,
                          annotation_text=f"Last High (Res): ₹{res_val:.2f}", annotation_position="top right")

            # Last Low (Support) Line
            fig.add_hline(y=sup_val, line_dash="dash", line_color="red", line_width=2,
                          annotation_text=f"Last Low (Sup): ₹{sup_val:.2f}", annotation_position="bottom right")

            fig.update_layout(
                title=f"{selected_symbol} - {selected_tf}",
                yaxis_title="Price (₹)",
                xaxis_title="Timeline",
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=550
            )

            st.plotly_chart(fig, use_container_width=True)
