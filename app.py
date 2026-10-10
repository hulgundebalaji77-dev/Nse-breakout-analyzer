import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="NSE Breakout & Support/Resistance", layout="wide")
st.title("NSE Stock Support & Resistance Analyzer")

ticker = st.text_input("Stock Ticker (e.g. KOTAKBANK.NS, SBIN.NS):", value="KOTAKBANK.NS")
period = st.selectbox("Period:", ["1mo", "3mo", "6mo", "1y"], index=2)
interval = st.selectbox("Interval:", ["5m", "15m", "1h", "1d"], index=3)

if st.button("Analyze"):
    # 1. Historical data fetch karne
    df = yf.download(ticker, period=period, interval=interval)

    if df.empty:
        st.error("Data bhetla nahi. Krupaya ticker symbol check kara.")
    else:
        # Multi-index columns flat karne (df aalyanantar)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 2. Moving Averages (EMA 9, 21, 50, 200)
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

        # 4. Safe Swing Support & Resistance Calculation
        window = 5
        highs = []
        lows = []

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
        latest_rsi = float(df["RSI"].iloc[-1])

        nearest_supports = sorted([s for s in set(lows) if s < current_price], reverse=True)[:3]
        nearest_resistances = sorted([r for r in set(highs) if r > current_price])[:3]

        # UI Display
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", f"{current_price:.2f}")
        col2.metric("RSI (14)", f"{latest_rsi:.2f}")
        col3.metric("EMA 200", f"{float(df['EMA_200'].iloc[-1]):.2f}")

        st.subheader("Nearest Support & Resistance Levels")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Support Levels:**")
            for s in nearest_supports:
                st.write(f"- {s:.2f}")
        with c2:
            st.write("**Resistance Levels:**")
            for r in nearest_resistances:
                st.write(f"- {r:.2f}")

        st.line_chart(df[["Close", "EMA_9", "EMA_21", "EMA_50", "EMA_200"]])
