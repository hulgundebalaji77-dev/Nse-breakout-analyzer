import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Actual S&R Level Finder", layout="wide")
st.title("🎯 Actual Price-Action Support & Resistance Scanner")

# ----------------- Stock List -----------------
NIFTY_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "TATAMOTORS", "SBIN", "BHARTIARTL",
    "ITC", "LT", "HINDUNILVR", "BAJFINANCE", "HINDPETRO", "JIOFIN", "BDL", "TRENT",
    "RECLTD", "LAURUSLABS", "MOTHERSON", "AXISBANK", "KOTAKBANK", "MARUTI", "SUNPHARMA"
]

st.sidebar.header("⚙️ सेटिंग्ज")
tf_choice = st.sidebar.selectbox("टाइमफ्रेम निवडा:", ["1 तास (1h)", "1 दिवस (Daily)", "15 मिनिटे (15m)"], index=0)

TF_CONFIG = {
    "15 मिनिटे (15m)": {"interval": "15m", "period": "7d", "order": 3},
    "1 तास (1h)": {"interval": "60m", "period": "1mo", "order": 4},
    "1 दिवस (Daily)": {"interval": "1d", "period": "1y", "order": 5}
}

cfg = TF_CONFIG[tf_choice]
scan_btn = st.sidebar.button("🚀 Actual Levels स्कॅन करा")

# ----------------- खरे Turn-Points शोधण्याचे लॉजिक -----------------
def extract_actual_sr_levels(df, order=4):
    """
    स्थानिक High आणि Low (Fractal Swings) शोधून क्लस्टर तयार करणे
    """
    highs = []
    lows = []
    
    # चालू कॅन्डल सोडून मागील डेटा तपासणे
    sub_df = df.iloc[:-1]
    
    for i in range(order, len(sub_df) - order):
        # Swing High (Resistance Pivot)
        if sub_df['High'].iloc[i] == sub_df['High'].iloc[i - order : i + order + 1].max():
            highs.append(sub_df['High'].iloc[i])
            
        # Swing Low (Support Pivot)
        if sub_df['Low'].iloc[i] == sub_df['Low'].iloc[i - order : i + order + 1].min():
            lows.append(sub_df['Low'].iloc[i])
            
    return sorted(lows), sorted(highs)

def group_close_levels(levels, threshold_pct=0.8):
    """
    जवळपासच्या लेव्हल्स एकत्र करून एक मजबूत S&R लाईन बनवणे
    """
    if not levels:
        return []
    clusters = []
    curr_cluster = [levels[0]]
    
    for val in levels[1:]:
        if (val - curr_cluster[-1]) / curr_cluster[-1] * 100 <= threshold_pct:
            curr_cluster.append(val)
        else:
            clusters.append(np.mean(curr_cluster))
            curr_cluster = [val]
    clusters.append(np.mean(curr_cluster))
    return sorted(clusters)

# ----------------- स्कॅनर -----------------
def run_actual_scanner(symbols, interval, period, order):
    tickers = [f"{s}.NS" for s in symbols]
    raw = yf.download(tickers=tickers, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    
    results = []
    
    for sym in symbols:
        tkr = f"{sym}.NS"
        try:
            if tkr not in raw.columns.levels[0]:
                continue
            df = raw[tkr].dropna()
            if len(df) < 30:
                continue
                
            curr_close = float(df['Close'].iloc[-1])
            curr_high = float(df['High'].iloc[-1])
            curr_low = float(df['Low'].iloc[-1])
            
            raw_lows, raw_highs = extract_actual_sr_levels(df, order=order)
            
            major_supports = group_close_levels(raw_lows)
            major_resistances = group_close_levels(raw_highs)
            
            # LTP च्या सर्वात जवळचा खरा सपोर्ट आणि रेझिस्टन्स
            below_levels = [l for l in major_supports if l < curr_close]
            above_levels = [h for h in major_resistances if h > curr_close]
            
            actual_support = max(below_levels) if below_levels else None
            actual_resistance = min(above_levels) if above_levels else None
            
            match_found = False
            status = "Trading in Range"
            target_level = None
            diff_pct = 0.0
            
            # Support Test तपासणी (Low लेव्हलजवळ आला का)
            if actual_support:
                sup_dist = (curr_close - actual_support) / curr_close * 100
                low_dist = abs(curr_low - actual_support) / actual_support * 100
                if sup_dist <= 0.6 or low_dist <= 0.4:
                    match_found = True
                    status = "🟢 At Major Support"
                    target_level = actual_support
                    diff_pct = sup_dist

            # Resistance Test तपासणी (High लेव्हलजवळ आला का)
            if actual_resistance and not match_found:
                res_dist = (actual_resistance - curr_close) / curr_close * 100
                high_dist = abs(curr_high - actual_resistance) / actual_resistance * 100
                if res_dist <= 0.6 or high_dist <= 0.4:
                    match_found = True
                    status = "🔴 At Major Resistance"
                    target_level = actual_resistance
                    diff_pct = res_dist
                    
            if match_found:
                results.append({
                    "Symbol": sym,
                    "LTP (₹)": round(curr_close, 2),
                    "Status": status,
                    "Matched Level (₹)": round(target_level, 2),
                    "अंतर (%)": round(diff_pct, 2),
                    "Next Support": round(actual_support, 2) if actual_support else "-",
                    "Next Resistance": round(actual_resistance, 2) if actual_resistance else "-"
                })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# ----------------- UI -----------------
if scan_btn:
    st.session_state.pop('res_df', None)
    with st.spinner(f"'{tf_choice}' वर खऱ्या रिव्हर्सल लेव्हल्स शोधत आहे..."):
        res_df = run_actual_scanner(NIFTY_STOCKS, cfg["interval"], cfg["period"], cfg["order"])
        st.session_state['res_df'] = res_df
        st.session_state['current_tf'] = tf_choice

if 'res_df' in st.session_state:
    res_df = st.session_state['res_df']
    cur_tf = st.session_state.get('current_tf', tf_choice)
    
    if not res_df.empty:
        st.success(f"🎯 खऱ्या S&R झोनजवळ सापडलेले शेअर्स: {len(res_df)} ({cur_tf})")
        st.dataframe(res_df.sort_values(by="अंतर (%)"), use_container_width=True)
        
        st.markdown("---")
        pick = st.selectbox("चार्टवर S&R लेव्हल्स पाहण्यासाठी शेअर निवडा:", res_df["Symbol"].unique())
        if pick:
            chart_df = yf.download(f"{pick}.NS", period=cfg["period"], interval=cfg["interval"], progress=False)
            r_lows, r_highs = extract_actual_sr_levels(chart_df, order=cfg["order"])
            sups = group_close_levels(r_lows)
            ress = group_close_levels(r_highs)
            
            fig = go.Figure(data=[go.Candlestick(
                x=chart_df.index,
                open=chart_df['Open'],
                high=chart_df['High'],
                low=chart_df['Low'],
                close=chart_df['Close'],
                name="Price"
            )])
            
            # प्रत्यक्षात सापडलेले सर्व महत्त्वाचे सपोर्ट (हिरव्या रेषा)
            for s in sups[-3:]:
                fig.add_hline(y=s, line_dash="dash", line_color="green", annotation_text=f"Sup: ₹{s:.1f}")
                
            # प्रत्यक्षात सापडलेले सर्व महत्त्वाचे रेझिस्टन्स (लाल रेषा)
            for r in ress[-3:]:
                fig.add_hline(y=r, line_dash="dash", line_color="red", annotation_text=f"Res: ₹{r:.1f}")
                
            fig.update_layout(title=f"{pick} - Actual Swings ({cur_tf})", xaxis_rangeslider_visible=False, height=520)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("या टाइमफ्रेमवर सध्या कोणताही शेअर अगदी लेव्हलजवळ (0.6% च्या आत) नाही.")
