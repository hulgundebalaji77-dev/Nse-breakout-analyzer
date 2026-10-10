import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Nifty 200 Breakout & Levels Analyzer", layout="wide")
st.title("NSE Nifty 200 Support & Resistance Analyzer")

# Nifty 200 Stocks chi List
NIFTY_200_TICKERS = [
    "ABB.NS", "ACC.NS", "APLAPOLLO.NS", "AUBANK.NS", "ADANIENSOL.NS", "ADANIENT.NS", "ADANIGREEN.NS",
    "ADANIPORTS.NS", "ADANIPOWER.NS", "ATGL.NS", "ABCAPITAL.NS", "ABFRL.NS", "ALKEM.NS", "AMBUJACEM.NS",
    "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "AUROPHARMA.NS",
    "DMART.NS", "AXISBANK.NS", "BSE.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BAJAJHLDNG.NS",
    "BALKRISIND.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BANKINDIA.NS", "BERGEPAINT.NS", "BEL.NS",
    "BHARATFORG.NS", "BHEL.NS", "BPCL.NS", "BHARTIARTL.NS", "BIOCON.NS", "BOSCHLTD.NS", "BRITANNIA.NS",
    "CANBK.NS", "CGPOWER.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COFORGE.NS", "COLPAL.NS",
    "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS", "DLF.NS", "DABUR.NS", "DALBHARAT.NS",
    "DEEPAKNTR.NS", "DELHIVERY.NS", "DIVISLAB.NS", "DIXON.NS", "LALPATHLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "ESCORTS.NS", "EXIDEIND.NS", "NYKAA.NS", "FEDERALBNK.NS", "FACT.NS", "FORTIS.NS", "GAIL.NS",
    "GMRINFRA.NS", "GLENMARK.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRASIM.NS", "GUJGASLTD.NS", "HCLTECH.NS",
    "HDFCAMC.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HAVELLS.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HAL.NS",
    "HINDCOPPER.NS", "HINDPETRO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS",
    "IDFCFIRSTB.NS", "IPCALAB.NS", "IRB.NS", "ITC.NS", "INDIANB.NS", "INDHOTEL.NS", "IOC.NS", "IRCTC.NS",
    "IRFC.NS", "IGL.NS", "INDUSTOWER.NS", "INDUSINDBK.NS", "NAUKRI.NS", "INFY.NS", "INDIGO.NS", "JSWENERGY.NS",
    "JSWINFRA.NS", "JSWSTEEL.NS", "JINDALSTEL.NS", "JIOFIN.NS", "JUBLFOOD.NS", "KEI.NS", "KALYANKJIL.NS",
    "KOTAKBANK.NS", "L&TFH.NS", "LTTS.NS", "LICHSGFIN.NS", "LTIM.NS", "LT.NS", "LAURUSLABS.NS", "LICI.NS",
    "LUPIN.NS", "MRF.NS", "LODHA.NS", "M&MFIN.NS", "M&M.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS",
    "MAXHEALTH.NS", "MAZDOCK.NS", "MPHASIS.NS", "MUTHOOTFIN.NS", "NHPC.NS", "NMDC.NS", "NTPC.NS",
    "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "OBEROIRLTY.NS", "ONGC.NS", "OIL.NS", "PAYTM.NS",
    "OFSS.NS", "PAGEIND.NS", "PATANJALI.NS", "PERSISTENT.NS", "PETRONET.NS", "PIDILITIND.NS", "PEL.NS",
    "POLYCAB.NS", "POONAWALLA.NS", "PFC.NS", "POWERGRID.NS", "PRESTIGE.NS", "PNB.NS", "RECLTD.NS",
    "RELIANCE.NS", "SBICARD.NS", "SBILIFE.NS", "SJVN.NS", "SRF.NS", "MOTHERSON.NS", "SHREECEM.NS",
    "SHRIRAMFIN.NS", "SIEMENS.NS", "SOLARINDS.NS", "SONACOMS.NS", "SBIN.NS", "SAIL.NS", "SUNPHARMA.NS",
    "SUNTV.NS", "SUZLON.NS", "SYNGENE.NS", "TVSMOTOR.NS", "TATACHEM.NS", "TATACOMM.NS", "TCS.NS",
    "TATACONSUM.NS", "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TATATECH.NS",
    "TECHM.NS", "TITAN.NS", "TORNTPHARM.NS", "TORNTPOWER.NS", "TRENT.NS", "TIINDIA.NS", "UPL.NS",
    "ULTRACEMCO.NS", "UNIONBANK.NS", "UBL.NS", "UNITDSPR.NS", "VBL.NS", "VEDL.NS", "VOLTAS.NS",
    "WIPRO.NS", "YESBANK.NS", "ZEEL.NS", "ZYDUSLIFE.NS"
]

# Sidebar Controls
st.sidebar.header("Settings")
selected_ticker = st.sidebar.selectbox("Nifty 200 Stock Nivadha:", NIFTY_200_TICKERS, index=NIFTY_200_TICKERS.index("KOTAKBANK.NS"))
period = st.sidebar.selectbox("Period:", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
interval = st.sidebar.selectbox("Interval:", ["5m", "15m", "1h", "1d"], index=3)
window = st.sidebar.slider("Swing Lookback Window:", min_value=2, max_value=10, value=5)

def analyze_stock(ticker):
    # 1. Historical data fetch
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty:
        return None, None, None, None

    # Multi-index columns flat karne
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2. Indicators (EMA 9, 21, 50, 200)
    df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

    # 3. RSI 14
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # 4. Safe Swing Support & Resistance
    highs, lows = [], []
    for i in range(window, len(df) - window):
        current_high = float(df["High"].iloc[i])
        current_low = float(df["Low"].iloc[i])
        prev_highs = df["High"].iloc[i - window : i + window + 1]
        prev_lows = df["Low"].iloc[i - window : i + window + 1]

        if current_high == float(prev_highs.max()):
            highs.append(current_high)
        if current_low == float(prev_lows.min()):
            lows.append(current_low)

    current_price = float(df["Close"].iloc[-1])
    supports = sorted([s for s in set(lows) if s < current_price], reverse=True)[:3]
    resistances = sorted([r for r in set(highs) if r > current_price])[:3]

    return df, current_price, supports, resistances

# Main Analysis
df, current_price, supports, resistances = analyze_stock(selected_ticker)

if df is not None:
    st.subheader(f"{selected_ticker} Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"₹{current_price:.2f}")
    col2.metric("RSI (14)", f"{float(df['RSI'].iloc[-1]):.2f}")
    col3.metric("EMA 50", f"₹{float(df['EMA_50'].iloc[-1]):.2f}")
    col4.metric("EMA 200", f"₹{float(df['EMA_200'].iloc[-1]):.2f}")

    c1, c2 = st.columns(2)
    with c1:
        st.success("### Nearest Support Levels")
        if supports:
            for s in supports:
                st.write(f"- **₹{s:.2f}**")
        else:
            st.write("Major support sapadla nahi.")

    with c2:
        st.error("### Nearest Resistance Levels")
        if resistances:
            for r in resistances:
                st.write(f"- **₹{r:.2f}**")
        else:
            st.write("All-time high javal ahe (Resistance nahi).")

    st.subheader("Price & EMA Chart")
    st.line_chart(df[["Close", "EMA_9", "EMA_21", "EMA_50", "EMA_200"]])
else:
    st.warning("Data load karnyat adchan aali. Krupaya punha prayatna kara.")
