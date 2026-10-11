import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="NSE 200 Multi-Timeframe S&R Screener", layout="wide")

st.title("📈 NSE Top 200 Support & Resistance Screener")
st.caption("Custom Timeframe Support/Resistance Breakout & Breakdown Scanner")

# NSE 200 मधील प्रमुख स्टॉक्स (प्रातिनिधिक यादी)
NIFTY_200_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", "ITC.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "ADANIENT.NS", "TATAMOTORS.NS", "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS",
    "NTPC.NS", "AXISBANK.NS", "DMART.NS", "POWERGRID.NS", "M&M.NS",
    "ADANIPORTS.NS", "COALINDIA.NS", "BAJAJFINSV.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "IOC.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "SIEMENS.NS", "GRASIM.NS",
    "BEL.NS", "HAL.NS", "VEDL.NS", "PIDILITIND.NS", "BPCL.NS",
    "DLF.NS", "INDIGO.NS", "EICHERMOT.NS", "TRENT.NS", "ZOMATO.NS",
    "CHOLAFIN.NS", "HINDALCO.NS", "DIVISLAB.NS", "CIPLA.NS", "TECHM.NS"
]

# --- साइडबार सेटिंग्ज ---
st.sidebar.header("⚙️ Scanner Settings")

# 1. Timeframe निवड
timeframe_labels = {
    "15 Minutes (Intraday)": {"interval": "15m", "period": "5d"},
    "1 Hour (Short Swing)": {"interval": "60m", "period": "1mo"},
    "1 Day (Daily Swing)": {"interval": "1d", "period": "6mo"},
    "1 Week (Positional)": {"interval": "1wk", "period": "2y"}
}

selected_tf_label = st.sidebar.selectbox(
    "Select Timeframe:",
    list(timeframe_labels.keys()),
    index=2  # Default: 1 Day
)

tf_config = timeframe_labels[selected_tf_label]
interval = tf_config["interval"]
period = tf_config["period"]

# 2. कॅन्डल्स लुकबॅक (Lookback Candles)
lookback_candles = st.sidebar.slider(
    "S&R Lookback (मागील Candles ची संख्या):", 
    min_value=10, 
    max_value=60, 
    value=20
)

# 3. Near S&R टॉलरन्स
tolerance_pct = st.sidebar.slider(
    "Near Breakout Margin (%):", 
    min_value=0.1, 
    max_value=2.0, 
    value=0.5, 
    step=0.1
)

# --- S&R कॅल्क्युलेशन फंक्शन ---
def analyze_stock(ticker, interval, period, lookback, tol):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty or len(df) < lookback + 5:
            return None
        
        # MultiIndex columns flatten करणे
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        current_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        
        # मागील लुकबॅक कॅन्डल्सचा High आणि Low (चालू कॅन्डल वगळून)
        high_series = df['High'].iloc[-(lookback + 1):-1]
        low_series = df['Low'].iloc[-(lookback + 1):-1]
        
        resistance = float(high_series.max())
        support = float(low_series.min())

        diff_r = ((current_close - resistance) / resistance) * 100
        diff_s = ((current_close - support) / support) * 100

        # Breakout / Breakdown स्टेटस
        if current_close > resistance:
            status = "🚀 Resistance Breakout"
        elif abs(diff_r) <= tol and current_close <= resistance:
            status = "⚠️ Near Resistance"
        elif current_close < support:
            status = "🔻 Support Breakdown"
        elif abs(diff_s) <= tol and current_close >= support:
            status = "⚠️ Near Support"
        else:
            status = "Rangebound"

        pct_change = ((current_close - prev_close) / prev_close) * 100

        return {
            "Symbol": ticker.replace(".NS", ""),
            "LTP (₹)": round(current_close, 2),
            "Change (%)": round(pct_change, 2),
            f"Resistance ({lookback} bars)": round(resistance, 2),
            f"Support ({lookback} bars)": round(support, 2),
            "Status": status
        }
    except Exception:
        return None

# --- स्कॅन ट्रिगर ---
if st.button(f"🔍 Scan Stocks on {selected_tf_label}"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, sym in enumerate(NIFTY_200_TICKERS):
        status_text.text(f"Scanning {sym} ({idx+1}/{len(NIFTY_200_TICKERS)})...")
        data = analyze_stock(sym, interval, period, lookback_candles, tolerance_pct)
        if data:
            results.append(data)
        progress_bar.progress((idx + 1) / len(NIFTY_200_TICKERS))

    status_text.empty()
    progress_bar.empty()

    if results:
        df_res = pd.DataFrame(results)

        breakouts = df_res[df_res['Status'] == "🚀 Resistance Breakout"]
        breakdowns = df_res[df_res['Status'] == "🔻 Support Breakdown"]
        near_levels = df_res[df_res['Status'].str.contains("Near")]

        col1, col2, col3 = st.columns(3)
        col1.metric("Resistance Breakouts", len(breakouts))
        col2.metric("Support Breakdowns", len(breakdowns))
        col3.metric("Near Levels Watchlist", len(near_levels))

        st.markdown(f"### निकाल: **{selected_tf_label}**")
        
        # फिल्टर: फक्त अ‍ॅक्शन घेण्यासारखे शेअर्स दाखवणे
        actionable = df_res[df_res['Status'] != "Rangebound"]
        if not actionable.empty:
            st.dataframe(actionable, use_container_width=True)
        else:
            st.info("या Timeframe वर सध्या कोणताही ब्रेकआऊट किंवा ब्रेकडाऊन मिळालेला नाही.")
            
        with st.expander("सर्व शेअर्सची यादी पहा (Rangebound सह)"):
            st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("डेटा फेच करताना अडचण आली. कृपया इंटरनेट तपासा.")
