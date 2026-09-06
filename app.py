import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import find_peaks

st.set_page_config(page_title="NSE Multi-Stock Breakout Scanner", layout="wide")
st.title("🎯 NSE Multi-Stock Breakout & Trend Scanner")

# प्रमुख NSE स्टॉक्सची यादी
DEFAULT_NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
    "SBIN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "ITC.NS", "LT.NS",
    "BSE.NS", "KPITTECH.NS", "CUMMINSIND.NS", "HAL.NS", "DIXON.NS",
    "BEL.NS", "TRENT.NS", "COALINDIA.NS", "M&M.NS", "SUNPHARMA.NS"
]

# मोड निवड
app_mode = st.sidebar.radio("मोड निवडा:", ["🚀 Multi-Stock Auto Scanner", "📈 Single Stock Chart Analyzer"])

# ----------------- मोड १: मल्टिपल स्टॉक्स ऑटो स्कॅनर -----------------
if app_mode == "🚀 Multi-Stock Auto Scanner":
    st.subheader("📊 सर्व NSE स्टॉक्स ब्रेकआउट स्कॅनर")
    st.write("खालील बटणावर क्लिक केल्यावर सर्व सिलेक्ट केलेल्या स्टॉक्समध्ये ब्रेकआउट झाला आहे का ते आपोआप स्कॅन होईल.")
    
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        selected_stocks = st.multiselect("स्कॅन करण्यासाठी स्टॉक्स निवडा:", DEFAULT_NSE_STOCKS, default=DEFAULT_NSE_STOCKS)
    with col_btn:
        st.write("")
        st.write("")
        scan_now = st.button("🔍 सर्व स्टॉक्स स्कॅन करा", use_container_width=True)

    if scan_now:
        results = []
        progress_bar = st.progress(0)
        
        for i, sym in enumerate(selected_stocks):
            progress_bar.progress((i + 1) / len(selected_stocks))
            try:
                # 6 महिन्यांचा डेटा डाऊनलोड
                df_stock = yf.download(sym, period="6mo", interval="1d", progress=False)
                if df_stock.empty or len(df_stock) < 30:
                    continue
                if isinstance(df_stock.columns, pd.MultiIndex):
                    df_stock.columns = df_stock.columns.get_level_values(0)
                
                highs = df_stock['High'].values
                lows = df_stock['Low'].values
                peaks, _ = find_peaks(highs, distance=5)
                troughs, _ = find_peaks(-lows, distance=5)

                if len(peaks) == 0 or len(troughs) == 0:
                    continue

                res_level = highs[peaks[-1]]
                sup_level = lows[troughs[-1]]
                ltp = df_stock['Close'].iloc[-1]
                prev_close = df_stock['Close'].iloc[-2]
                curr_vol = df_stock['Volume'].iloc[-1]
                avg_vol = df_stock['Volume'].iloc[-21:-1].mean()
                vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
                pct_chg = ((ltp - prev_close) / prev_close) * 100

                # स्थिती तपासणे
                status = "Consolidation"
                if ltp > res_level:
                    status = "🔥 Confirmed Breakout" if vol_ratio >= 1.5 else "⚠️ Weak Breakout"
                elif ltp < sup_level:
                    status = "🔻 Breakdown"

                results.append({
                    "Stock": sym,
                    "LTP (₹)": round(ltp, 2),
                    "Change %": round(pct_chg, 2),
                    "Resistance (₹)": round(res_level, 2),
                    "Support (₹)": round(sup_level, 2),
                    "Volume Ratio": f"{round(vol_ratio, 2)}x",
                    "Status": status
                })
            except Exception:
                continue

        progress_bar.empty()

        if results:
            res_df = pd.DataFrame(results)
            
            # ब्रेकआउट मिळालेले स्टॉक्स वेगळे दाखवणे
            breakouts = res_df[res_df["Status"].str.contains("Breakout")]
            if not breakouts.empty:
                st.success(f"🎉 *{len(breakouts)} स्टॉक्समध्ये ब्रेकआउट सापडला आहे!*")
                st.dataframe(breakouts, use_container_width=True)
            else:
                st.info("सध्या निवडलेल्या स्टॉक्सपैकी कोणामध्येही फ्रेश ब्रेकआउट नाही.")

            st.write("---")
            st.subheader("सर्व स्टॉक्सची स्थिती (Full Watchlist Status)")
            st.dataframe(res_df, use_container_width=True)

# ----------------- मोड २: सिंगल स्टॉक सविस्तर चार्ट -----------------
else:
    st.subheader("📈 सविस्तर कँडलस्टिक आणि ट्रेंडलाइन ॲनालिसिस")
    
    ticker_symbol = st.sidebar.text_input("NSE स्टॉक सिम्बॉल (.NS जोडा):", value="BSE.NS").upper()
    time_period = st.sidebar.selectbox("डेटा पिरियड:", ["3mo", "6mo", "1y"], index=1)
    peak_distance = st.sidebar.slider("Swing Sensitivity:", min_value=3, max_value=15, value=5)

    df = yf.download(ticker_symbol, period=time_period, interval="1d", progress=False)
    
    if df.empty:
        st.error("डेटा लोड करता आला नाही. कृपया सिम्बॉल तपासा.")
    else:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)

        high_prices = df['High'].values
        low_prices = df['Low'].values
        peaks, _ = find_peaks(high_prices, distance=peak_distance)
        troughs, _ = find_peaks(-low_prices, distance=peak_distance)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"
        ))

        # ऑटो ट्रेंडलाइन्स
        if len(peaks) >= 2:
            p1, p2 = peaks[-2], peaks[-1]
            slope, intercept = np.polyfit([p1, p2], [high_prices[p1], high_prices[p2]], 1)
            ext_x = np.arange(p1, len(df))
            fig.add_trace(go.Scatter(x=df['Date'].iloc[ext_x], y=slope * ext_x + intercept,
                                     mode='lines', line=dict(color='red', width=2, dash='dash'), name="Resistance Trendline"))

        if len(troughs) >= 2:
            t1, t2 = troughs[-2], troughs[-1]
            slope_s, intercept_s = np.polyfit([t1, t2], [low_prices[t1], low_prices[t2]], 1)
            ext_x_s = np.arange(t1, len(df))
            fig.add_trace(go.Scatter(x=df['Date'].iloc[ext_x_s], y=slope_s * ext_x_s + intercept_s,
                                     mode='lines', line=dict(color='green', width=2, dash='dash'), name="Support Trendline"))

        fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
