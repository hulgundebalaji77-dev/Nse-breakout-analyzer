import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Nifty Price Match Scanner", layout="wide")
st.title("🎯 Nifty Price Match: Real Swing & EMA Levels")

# ----------------- Stock List -----------------
NIFTY_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "TATAMOTORS", "SBIN", "BHARTIARTL",
    "ITC", "LT", "HINDUNILVR", "BAJFINANCE", "HINDPETRO", "JIOFIN", "BDL", "TRENT",
    "RECLTD", "LAURUSLABS", "MOTHERSON", "AXISBANK", "KOTAKBANK", "MARUTI", "SUNPHARMA",
    "TITAN", "ULTRACEMCO", "ASIANPAINT", "NTPC", "ONGC", "POWERGRID", "COALINDIA",
    "ADANIENT", "ADANIPORTS", "BPCL", "IOC", "CIPLA", "DRREDDY", "WIPRO", "HCLTECH"
]

# ----------------- Sidebar -----------------
st.sidebar.header("⚙️ स्कॅनर सेटिंग्ज")

tf_choice = st.sidebar.selectbox(
    "टाइमफ्रेम निवडा:",
    ["1 तास (Short Term)", "1 दिवस (Daily Swing)", "15 मिनिटे (Intraday)", "1 आठवडा (Positional)"],
    index=0
)

TF_MAP = {
    "15 मिनिटे (Intraday)": {"interval": "15m", "period": "5d"},
    "1 तास (Short Term)": {"interval": "60m", "period": "1mo"},
    "1 दिवस (Daily Swing)": {"interval": "1d", "period": "1y"},
    "1 आठवडा (Positional)": {"interval": "1wk", "period": "2y"}
}

interval = TF_MAP[tf_choice]["interval"]
period = TF_MAP[tf_choice]["period"]

tolerance = st.sidebar.slider("Tolerance / मॅच अंतर (%):", min_value=0.1, max_value=1.5, value=0.4, step=0.05)
scan_clicked = st.sidebar.button("🚀 शेअर्स स्कॅन करा")

# ----------------- Scanner Logic -----------------
def get_pivots_and_matches(symbols, interval, period, tol):
    matched = []
    tickers = [f"{s}.NS" for s in symbols]
    
    # थेट फ्रेश डेटा डाऊनलोड
    data = yf.download(tickers=tickers, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    
    for sym in symbols:
        ticker = f"{sym}.NS"
        try:
            if ticker not in data.columns.levels[0]:
                continue
            df = data[ticker].dropna()
            if len(df) < 25:
                continue
                
            curr = df.iloc[-1]
            c_close = float(curr['Close'])
            c_high = float(curr['High'])
            c_low = float(curr['Low'])

            # 1. EMA Levels (चार्टप्रमाणे)
            ema20 = float(df['Close'].ewm(span=20, adjust=False).mean().iloc[-1])
            ema50 = float(df['Close'].ewm(span=50, adjust=False).mean().iloc[-1])
            ema200 = float(df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]) if len(df) >= 200 else None

            # 2. अस्सल Swing Resistance (High) & Swing Support (Low) - चालू कॅन्डल वगळून
            hist_df = df.iloc[:-1]
            swing_high = float(hist_df['High'].tail(15).max())
            swing_low = float(hist_df['Low'].tail(15).min())

            levels = {
                "Swing Resistance": swing_high,
                "Swing Support": swing_low,
                "20 EMA": ema20,
                "50 EMA": ema50
            }
            if ema200:
                levels["200 EMA"] = ema200

            for lvl_name, lvl_val in levels.items():
                close_diff = abs(c_close - lvl_val) / lvl_val * 100
                low_diff = abs(c_low - lvl_val) / lvl_val * 100
                high_diff = abs(c_high - lvl_val) / lvl_val * 100

                is_hit = False
                status = ""

                # सपोर्ट मॅच (Swing Low किंवा EMA वर प्राईस सपोर्ट घेत असेल)
                if ("Support" in lvl_name) or ("EMA" in lvl_name and c_close >= lvl_val):
                    if low_diff <= tol or close_diff <= tol:
                        is_hit = True
                        status = f"🟢 Support Tested ({lvl_name})"

                # रेझिस्टन्स मॅच (Swing High किंवा EMA वर प्राईस रेझिस्टन्स घेत असेल)
                elif ("Resistance" in lvl_name) or ("EMA" in lvl_name and c_close <= lvl_val):
                    if high_diff <= tol or close_diff <= tol:
                        is_hit = True
                        status = f"🔴 Resistance Tested ({lvl_name})"

                if is_hit:
                    matched.append({
                        "Symbol": sym,
                        "LTP (₹)": round(c_close, 2),
                        "Status": status,
                        "Matched Level": lvl_name,
                        "Level Price (₹)": round(lvl_val, 2),
                        "फरक (₹)": round(c_close - lvl_val, 2),
                        "फरक (%)": round(close_diff, 2)
                    })
                    break
        except Exception:
            continue
            
    return pd.DataFrame(matched)

# ----------------- UI Execution -----------------
if scan_clicked:
    # जुना कॅश पूर्ण क्लिअर करून फ्रेश रन
    st.session_state.pop('scan_results', None)
    with st.spinner(f"'{tf_choice}' डेटा स्कॅन होत आहे..."):
        res_df = get_pivots_and_matches(NIFTY_STOCKS, interval, period, tolerance)
        st.session_state['scan_results'] = res_df
        st.session_state['active_tf'] = tf_choice

if 'scan_results' in st.session_state:
    res_df = st.session_state['scan_results']
    current_tf = st.session_state.get('active_tf', tf_choice)
    
    if not res_df.empty:
        st.success(f"🎯 सापडलेले शेअर्स: {len(res_df)} (Timeframe: {current_tf})")
        st.dataframe(res_df.sort_values(by="फरक (%)"), use_container_width=True)
        
        # Chart
        st.markdown("---")
        pick_stock = st.selectbox("चार्ट पाहण्यासाठी शेअर निवडा:", res_df["Symbol"].unique())
        if pick_stock:
            chart_df = yf.download(f"{pick_stock}.NS", period=period, interval=interval, progress=False)
            row = res_df[res_df["Symbol"] == pick_stock].iloc[0]
            
            fig = go.Figure(data=[go.Candlestick(
                x=chart_df.index,
                open=chart_df['Open'],
                high=chart_df['High'],
                low=chart_df['Low'],
                close=chart_df['Close'],
                name="किंमत"
            )])
            
            fig.add_hline(
                y=row['Level Price (₹)'], 
                line_dash="solid", 
                line_color="gold", 
                line_width=2.5,
                annotation_text=f"Matched: {row['Matched Level']} (₹{row['Level Price (₹)']})"
            )
            
            fig.update_layout(
                title=f"{pick_stock} ({current_tf}) - {row['Matched Level']}", 
                xaxis_rangeslider_visible=False, 
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"'{current_tf}' मध्ये दिलेल्या Tolerance वर कोणताही शेअर मॅच झाला नाही. कृपया Tolerance थोडे वाढवा.")
