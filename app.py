import numpy as np
import pandas as pd
import yfinance as yf


def calculate_indicators_and_levels(ticker="KOTAKBANK.NS", period="6mo", interval="1d"):
    # 1. Historical data fetch karne
    df = yf.download(ticker, period=period, interval=interval)
    if df.empty:
        return "Data bhetla nahi."

    # Multi-index columns flat karne (yfinance updates sathi)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2. Exponential Moving Averages (EMA 9, 21, 50, 200)
    df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

    # 3. RSI 14 Calculation
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # 4. Accurate Support ani Resistance levels (Fractal / Swing Points)
    window = 5  # Left ani Right bars count
    df["Is_Support"] = (
        df["Low"] == df["Low"].rolling(window=2 * window + 1, center=True).min()
    )
    df["Is_Resistance"] = (
        df["High"] == df["High"].rolling(window=2 * window + 1, center=True).max()
    )

    support_levels = df[df["Is_Support"]]["Low"].dropna().tolist()
    resistance_levels = df[df["Is_Resistance"]]["High"].dropna().tolist()

    # Current/Latest Values
    current_price = df["Close"].iloc[-1]
    latest_ema9 = df["EMA_9"].iloc[-1]
    latest_ema21 = df["EMA_21"].iloc[-1]
    latest_ema50 = df["EMA_50"].iloc[-1]
    latest_ema200 = df["EMA_200"].iloc[-1]
    latest_rsi = df["RSI"].iloc[-1]

    # Nearest Support ani Resistance filter karne
    nearest_supports = sorted([s for s in support_levels if s < current_price], reverse=True)[:3]
    nearest_resistances = sorted([r for r in resistance_levels if r > current_price])[:3]

    print(f"--- {ticker} Analysis ---")
    print(f"Current Price: {current_price:.2f}")
    print(f"RSI (14): {latest_rsi:.2f}")
    print(f"EMA 9: {latest_ema9:.2f} | EMA 21: {latest_ema21:.2f}")
    print(f"EMA 50: {latest_ema50:.2f} | EMA 200: {latest_ema200:.2f}")
    print("\nNearest Support Levels:")
    for s in nearest_supports:
        print(f"  -> {s:.2f}")
    print("\nNearest Resistance Levels:")
    for r in nearest_resistances:
        print(f"  -> {r:.2f}")

    return df

if __name__ == "__main__":
    calculate_indicators_and_levels("KOTAKBANK.NS")
