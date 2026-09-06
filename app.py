import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import find_peaks

st.set_page_config(page_title="NSE F&O Full Breakout Scanner", layout="wide")
st.title("🎯 NSE F&O Breakout & Trend Scanner (All Stocks)")

# NSE F&O मधील प्रमुख १८०+ स्टॉक्सची संपूर्ण यादी (.NS सह)
FNO_STOCKS = [
    "AARTIIND.NS", "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", 
    "ADANIENT.NS", "ADANIPORTS.NS", "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", 
    "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", 
    "AUBANK.NS", "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", 
    "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", "BANKBARODA.NS", 
    "BATAINDIA.NS", "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", 
    "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", "BPCL.NS", "BRITANNIA.NS", "BSOFT.NS", 
    "CANBK.NS", "CANFINHOME.NS", "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS", 
    "COALINDIA.NS", "COFORGE.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", 
    "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS", 
    "DELHIVERY.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", 
    "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS", "GLENMARK.NS", "GMRINFRA.NS", 
    "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", "GUJGASLTD.NS", 
    "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFCAMC.NS", "HDFCBANK.NS", "HDFCLIFE.NS", 
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS", "HINDUNILVR.NS", 
    "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDEA.NS", "IDFCFIRSTB.NS", "IEX.NS", 
    "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", 
    "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IPCALAB.NS", "IRCTC.NS", "ITC.NS", 
    "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", 
    "LALPATHLAB.NS", "LAURUSLABS.NS", "LICHSGFIN.NS", "LT.NS", "LTF.NS", "LTIM.NS", 
    "LTTS.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", 
    "MARUTI.NS", "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MOTHERSON.NS", 
    "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NATIONALUM.NS", "NAUKRI.NS", "NAVINFLUOR.NS", 
    "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", "OFSS.NS", "ONGC.NS", 
    "PAGEIND.NS", "PEL.NS", "PERSISTENT.NS", "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", 
    "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", 
    "RBLBANK.NS", "RECLTD.NS", "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", 
    "SBIN.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", 
    "SUNTV.NS", "SYNGENE.NS", "TATACHEM.NS", "TATACOMM.NS", "TATACONSUM.NS", 
    "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", 
    "TORNTPHARM.NS", "TORNTPOWER.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", 
    "UPL.NS", "VEDL.NS", "VOLTAS.NS", "WIPRO.NS", "ZYDUSLIFE.NS"
]

app_mode = st.sidebar.radio("मोड निवडा:", ["🚀 Scan All F&O Stocks", "📈 Individual Chart Analyzer"])

# ----------------- मोड १: सर्व F&O स्टॉक्स स्कॅन -----------------
if app_mode == "🚀 Scan All F&O Stocks":
    st.subheader(f"📊 NSE F&O ब्रेकआउट स्कॅनर ({len(FNO_STOCKS)} स्टॉक्स)")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        min_vol_mult = st.slider("किमान व्हॉल्यूम पटीत (Volume Multiple vs 20 MA):", 1.0, 3.0, 1.5, 0.1)
    with col2:
        st.write("")
        st.write("")
        start_scan = st.button("⚡ संपूर्ण F&O लिस्ट स्कॅन करा", use_container_width=True)

    if start_scan:
        with st.spinner("सर्व F&O स्टॉक्सचा डेटा डाउनलोड आणि स्कॅन होत आहे... कृपया १०-१५ सेकंद थांबा."):
            # बॅच डाऊनलोड (सर्व स्टॉक्स एकत्र डाऊनलोड होतात)
            all_data = yf.download(FNO_STOCKS, period="6mo", interval="1d", group_by='ticker', progress=False)
            
            results = []
            for ticker in FNO_STOCKS:
                try:
                    df = all_data[ticker].dropna()
                    if df.empty or len(df) < 30:
                        continue
                    
                    highs = df['High'].values
                    lows = df['Low'].values
                    peaks, _ = find_peaks(highs, distance=5)
                    troughs, _ = find_peaks(-lows, distance=5)

                    if len(peaks) == 0 or len(troughs) == 0:
                        continue

                    res_level = highs[peaks[-1]]
                    sup_level = lows[troughs[-1]]
                    ltp = df['Close'].iloc[-1]
                    prev_close = df['Close'].iloc[-2]
                    curr_vol = df['Volume'].iloc[-1]
                    avg_vol = df['Volume'].iloc[-21:-1].mean()
                    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
                    pct_chg = ((ltp - prev_close) / prev_close) * 100

                    status = "Consolidation"
                    if ltp > res_level:
                        status = "🔥 Confirmed Breakout" if vol_ratio >= min_vol_mult else "⚠️ Weak Breakout"
                    elif ltp < sup_level:
                        status = "🔻 Breakdown"

                    results.append({
                        "Stock": ticker,
                        "LTP (₹)": round(ltp, 2),
                        "Change %": round(pct_chg, 2),
                        "Resistance (₹)": round(res_level, 2),
                        "Support (₹)": round(sup_level, 2),
                        "Volume Ratio": f"{round(vol_ratio, 2)}x",
                        "Status": status
                    })
                except Exception:
                    continue

        if results:
            res_df = pd.DataFrame(results)
            
            # फिल्टर: फक्त ब्रेकआउट झालेले शेअर्स
            breakouts = res_df[res_df["Status"].str.contains("Breakout")]
            
            st.success(f"✅ स्कॅनिंग पूर्ण! एकूण {len(results)} स्टॉक्स स्कॅन झाले.")
            
            st.subheader(f"🔥 ब्रेकआउट झालेले F&O शेअर्स ({len(breakouts)})")
            if not breakouts.empty:
                st.dataframe(breakouts.sort_values(by="Change %", ascending=False), use_container_width=True)
            else:
                st.info("आज कोणत्याही F&O शेअरने रेजिस्टन्स तोडलेला नाही.")

            st.write("---")
            with st.expander("सर्व F&O स्टॉक्सची यादी पहा"):
                st.dataframe(res_df, use_container_width=True)

# ----------------- मोड २: सिंगल चार्ट अनालिसिस -----------------
else:
    st.subheader("📈 F&O स्टॉक चार्ट व्ह्यूअर")
    selected_stock = st.selectbox("स्टॉक निवडा:", FNO_STOCKS, index=FNO_STOCKS.index("RELIANCE.NS"))
    
    df = yf.download(selected_stock, period="6mo", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.reset_index(inplace=True)

    highs = df['High'].values
    lows = df['Low'].values
    peaks, _ = find_peaks(highs, distance=5)
    troughs, _ = find_peaks(-lows, distance=5)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"
    ))

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        slope, intercept = np.polyfit([p1, p2], [highs[p1], highs[p2]], 1)
        ext_x = np.arange(p1, len(df))
        fig.add_trace(go.Scatter(x=df['Date'].iloc[ext_x], y=slope * ext_x + intercept,
                                 mode='lines', line=dict(color='red', width=2, dash='dash'), name="Resistance Trendline"))

    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        slope_s, intercept_s = np.polyfit([t1, t2], [lows[t1], lows[t2]], 1)
        ext_x_s = np.arange(t1, len(df))
        fig.add_trace(go.Scatter(x=df['Date'].iloc[ext_x_s], y=slope_s * ext_x_s + intercept_s,
                                 mode='lines', line=dict(color='green', width=2, dash='dash'), name="Support Trendline"))

    fig.update_layout(xaxis_rangeslider_visible=False, height=520, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
