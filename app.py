import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ----------------- App Config -----------------
st.set_page_config(page_title="Nifty S&R Scanner", layout="wide")
st.title("🎯 Nifty 200 Price Support & Resistance Scanner")

# ----------------- Stock List -----------------
# Nifty प्रमुख शेअर्सची सुरक्षित यादी (ज्यामुळे Cloud वर पेज ब्लँक पडत नाही)
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
    ["1 दिवस (Daily Swing)", "1 तास (Short Term)", "15 मिनिटे (Intraday)", "1 आठवडा (Positional)"],
    index=0
)

TF_MAP = {
    "15 मिनिटे (Intraday)": {"interval": "15m", "period": "5d"},
    "1 तास (Short Term)": {"interval": "60m", "period": "1mo"},
    "1 दिवस (Daily Swing)": {"interval": "1d", "period": "6mo"},
    "1 आठवडा (Positional)": {"interval": "1wk", "period": "1y"}
}

interval = TF_MAP[tf_choice]["interval"]
period = TF_MAP[tf_choice]["period"]

tolerance = st.sidebar.slider("Tolerance / अंतर (%):", min_value=0.1, max_value=2.0, value=0.5, step=0.1)

# स्कॅन ट्रिगर
scan_clicked = st.sidebar.button("🚀 शेअर्स स्कॅन करा")

# ----------------- Core Logic -----------------
def get_pivots_and_matches(symbols, interval, period, tol):
    matched = []
    tickers = [f"{s}.NS" for s in symbols]
    
    # Batch download
    data = yf.download(tickers=tickers, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    
    for sym in symbols:
        ticker = f"{sym}.NS"
        try:
            if ticker not in data.columns.levels[0]:
                continue
            df = data[ticker].dropna()
            if len(df) < 15:
                continue
                
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            c_close = float(curr['Close'])
            c_high = float(curr['High'])
            c_low = float(curr['Low'])
            
            # Pivot S1 & R1
            p = (prev['High'] + prev['Low'] + prev['Close']) / 3
            r1 = (2 * p) - prev['Low']
            s1 = (2 * p) - prev['High']
            
            # Swing High / Low (मागील 15 कॅन्डल्स)
            swing_high = float(df['High'].iloc[-15:-1].max())
            swing_low = float(df['Low'].iloc[-15:-1].min())
            
            levels = {
                "Swing Support": swing_low,
                "Support 1 (S1)": s1,
                "Swing Resistance": swing_high,
                "Resistance 1 (R1)": r1
            }
            
            for lvl_name, lvl_val in levels.items():
                diff_pct = abs(c_close - lvl_val) / lvl_val * 100
                low_diff = abs(c_low - lvl_val) / lvl_val * 100
                high_diff = abs(c_high - lvl_val) / lvl_val * 100
                
                is_hit = False
                status = ""
                
                if "Support" in lvl_name:
                    if low_diff <= tol or diff_pct <= tol:
                        is_hit = True
                        status = "🟢 Support Near / Tested"
                elif "Resistance" in lvl_name:
                    if high_diff <= tol or diff_pct <= tol:
                        is_hit = True
                        status = "🔴 Resistance Near / Tested"
                        
                if is_hit:
                    matched.append({
                        "Symbol": sym,
                        "LTP (₹)": round(c_close, 2),
                        "Status": status,
                        "Matched Level": lvl_name,
                        "Level Price (₹)": round(lvl_val, 2),
                        "फरक (%)": round(diff_pct, 2),
                        "S1": round(s1, 2),
                        "R1": round(r1, 2),
                        "Swing Low": round(swing_low, 2),
                        "Swing High": round(swing_high, 2)
                    })
                    break
        except Exception:
            continue
            
    return pd.DataFrame(matched)

# ----------------- Main UI -----------------
st.write("शेअर्सचे सपोर्ट आणि रेझिस्टन्स लेव्हल्स शोधण्यासाठी डाव्या बाजूला **'शेअर्स स्कॅन करा'** बटणावर क्लिक करा.")

if scan_clicked:
    with st.spinner("डेटा स्कॅन होत आहे, कृपया थांबा..."):
        res_df = get_pivots_and_matches(NIFTY_STOCKS, interval, period, tolerance)
        st.session_state['scan_results'] = res_df

if 'scan_results' in st.session_state:
    res_df = st.session_state['scan_results']
    if not res_df.empty:
        st.success(f"🎯 सापडलेले शेअर्स: {len(res_df)}")
        st.dataframe(res_df[["Symbol", "LTP (₹)", "Status", "Matched Level", "Level Price (₹)", "फरक (%)"]], use_container_width=True)
        
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
                name="Price"
            )])
            
            fig.add_hline(y=row['Level Price (₹)'], line_dash="solid", line_color="gold", line_width=2.5,
                          annotation_text=f"Matched: {row['Matched Level']} (₹{row['Level Price (₹)']})")
            fig.add_hline(y=row['R1'], line_dash="dash", line_color="red", annotation_text="R1")
            fig.add_hline(y=row['S1'], line_dash="dash", line_color="green", annotation_text="S1")
            
            fig.update_layout(title=f"{pick_stock} Chart", xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("दिलेल्या Tolerance मध्ये कोणताही शेअर मॅच झाला नाही. कृपया Tolerance वाढवून पुन्हा स्कॅन करा.")
