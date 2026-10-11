import streamlit as st
import pandas as pd
import pyotp
from SmartApi import SmartConnect
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Angel One S&R Screener", layout="wide")

st.title("🎯 Angel One SmartAPI - Accurate S&R Screener")

# --- 1. Angel One Credentials Configuration ---
st.sidebar.header("🔐 SmartAPI Login Details")
API_KEY = st.sidebar.text_input("API Key", value="YOUR_API_KEY", type="password")
CLIENT_CODE = st.sidebar.text_input("Client Code", value="YOUR_CLIENT_CODE")
MPIN = st.sidebar.text_input("MPIN", value="YOUR_MPIN", type="password")
TOTP_SECRET = st.sidebar.text_input("TOTP Secret Key", value="YOUR_TOTP_KEY", type="password")

# --- 2. SmartAPI Timeframe Mapping ---
TIMEFRAME_MAP = {
    "5 Minutes (Intraday)": {"interval": "FIVE_MINUTE", "days": 2},
    "15 Minutes": {"interval": "FIFTEEN_MINUTE", "days": 5},
    "1 Hour (Screenshot Match)": {"interval": "ONE_HOUR", "days": 15},
    "1 Day (Daily Swing)": {"interval": "ONE_DAY", "days": 60}
}

selected_tf = st.sidebar.selectbox("Select Timeframe:", list(TIMEFRAME_MAP.keys()), index=2)
tf_config = TIMEFRAME_MAP[selected_tf]

# Angel One NSE Token Mapping (TCS, Reliance, etc.)
STOCK_TOKENS = {
    "TCS": "11536",
    "RELIANCE": "2885",
    "HDFCBANK": "1333",
    "INFY": "1594",
    "ICICIBANK": "4963",
    "SBIN": "3045",
    "LT": "11483",
    "BHARTIARTL": "10604",
    "ITC": "1660",
    "TATAMOTORS": "3456"
}

# --- 3. Angel One Login Function ---
@st.cache_resource
def get_smart_session(api_key, client_code, mpin, totp_key):
    try:
        smart_api = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_key).now()
        data = smart_api.generateSession(client_code, mpin, totp)
        if data['status']:
            return smart_api
        return None
    except Exception as e:
        st.sidebar.error(f"Login Error: {e}")
        return None

# --- 4. Fetch Accurate Candle Data ---
def fetch_angel_candles(smart_api, token, interval, days_back):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)

        historic_param = {
            "exchange": "NSE",
            "symboltoken": str(token),
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d 09:15"),
            "todate": to_date.strftime("%Y-%m-%d 15:30")
        }

        res = smart_api.getCandleData(historic_param)
        if not res or 'data' not in res or not res['data']:
            return None

        # Dataframe build karne: [Timestamp, Open, High, Low, Close, Volume]
        df = pd.DataFrame(res['data'], columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = df[col].astype(float)

        return df
    except Exception:
        return None

# --- 5. Breakout Logic ---
def check_angel_breakout(df, symbol):
    if df is None or len(df) < 3:
        return None

    # Magchi purna jhaleli candle (-2) ani chalu running candle (-1)
    prev_candle = df.iloc[-2]
    curr_candle = df.iloc[-1]

    last_high = float(prev_candle['High'])
    last_low = float(prev_candle['Low'])
    ltp = float(curr_candle['Close'])

    status = "Inside Range"
    if ltp > last_high:
        status = "🚀 Resistance Breakout"
    elif ltp < last_low:
        status = "🔻 Support Breakdown"

    pct_chg = ((ltp - float(prev_candle['Close'])) / float(prev_candle['Close'])) * 100

    return {
        "Symbol": symbol,
        "LTP (₹)": round(ltp, 2),
        "Candle Chg (%)": round(pct_chg, 2),
        "Last High (Res)": round(last_high, 2),
        "Last Low (Sup)": round(last_low, 2),
        "Candle Time": prev_candle['Datetime'].strftime("%d-%b %H:%M"),
        "Status": status
    }

# --- 6. Execution & Scanner Interface ---
api_client = None
if API_KEY != "YOUR_API_KEY" and CLIENT_CODE != "YOUR_CLIENT_CODE":
    api_client = get_smart_session(API_KEY, CLIENT_CODE, MPIN, TOTP_SECRET)

if st.button(f"🔍 Scan Stocks via Angel One ({selected_tf})"):
    if not api_client:
        st.error("Krupaya sidebar madhe accurate Angel One Credentials taka.")
    else:
        results = []
        prog = st.progress(0)
        stat = st.empty()

        for idx, (sym, tok) in enumerate(STOCK_TOKENS.items()):
            stat.text(f"Fetching live feed for {sym} ({idx+1}/{len(STOCK_TOKENS)})...")
            df_stock = fetch_angel_candles(api_client, tok, tf_config["interval"], tf_config["days"])
            info = check_angel_breakout(df_stock, sym)
            if info:
                results.append(info)
            prog.progress((idx + 1) / len(STOCK_TOKENS))

        stat.empty()
        prog.empty()

        if results:
            st.session_state["angel_results"] = pd.DataFrame(results)

# Display Screener Results
if "angel_results" in st.session_state:
    res_df = st.session_state["angel_results"]
    breakouts = res_df[res_df['Status'] == "🚀 Resistance Breakout"]
    breakdowns = res_df[res_df['Status'] == "🔻 Support Breakdown"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Resistance Breakouts", len(breakouts))
    c2.metric("Support Breakdowns", len(breakdowns))
    c3.metric("Inside Range", len(res_df) - len(breakouts) - len(breakdowns))

    st.subheader(f"📊 Breakout List (100% Live Angel Feed)")
    action_table = res_df[res_df['Status'] != "Inside Range"]
    if not action_table.empty:
        st.dataframe(action_table, use_container_width=True)
    else:
        st.info("Sadhya ya timeframe var kontahi breakout jhala nahi.")

    # --- Candlestick Chart View ---
    st.markdown("---")
    st.subheader("🕯️ Live Angel One Candlestick Chart")
    sel_sym = st.selectbox("Stock nivaada:", list(STOCK_TOKENS.keys()))

    if sel_sym and api_client:
        token = STOCK_TOKENS[sel_sym]
        chart_df = fetch_angel_candles(api_client, token, tf_config["interval"], tf_config["days"])

        if chart_df is not None and not chart_df.empty:
            plot_candles = chart_df.tail(40)
            res_p = float(plot_candles['High'].iloc[-2])
            sup_p = float(plot_candles['Low'].iloc[-2])

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=plot_candles['Datetime'].dt.strftime('%d-%b %H:%M'),
                open=plot_candles['Open'],
                high=plot_candles['High'],
                low=plot_candles['Low'],
                close=plot_candles['Close'],
                name=sel_sym
            ))

            fig.add_hline(y=res_p, line_dash="dash", line_color="green", line_width=2,
                          annotation_text=f"Res (High): ₹{res_p:.2f}", annotation_position="top right")
            fig.add_hline(y=sup_p, line_dash="dash", line_color="red", line_width=2,
                          annotation_text=f"Sup (Low): ₹{sup_p:.2f}", annotation_position="bottom right")

            fig.update_layout(
                title=f"{sel_sym} — Angel One Official Live Candle Chart",
                yaxis_title="Price (₹)",
                xaxis_title="Time",
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=520
            )

            st.plotly_chart(fig, use_container_width=True)
