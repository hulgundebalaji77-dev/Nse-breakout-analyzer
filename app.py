import yfinance as yf
import pandas as pd
import numpy as np

def calculate_robust_sr(df, window=5, cluster_threshold=0.012):
    """
    df: Candlestick DataFrame (High, Low, Close, Volume)
    window: Peak / Trough confirm karnyasathi candles (Fractals)
    cluster_threshold: Ekach zonemadhil levels ekatra karnyacha percentage (1.2%)
    """
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    n = len(df)
    
    raw_resistances = []
    raw_supports = []
    
    # 1. Swing Highs ani Swing Lows shodhane (Fractal Pivot points)
    for i in range(window, n - window):
        # Resistance condition: ithli price aagodar chya ani pudhchya 'window' candles peksha jast ahe
        if highs[i] == max(highs[i - window : i + window + 1]):
            raw_resistances.append(highs[i])
            
        # Support condition: ithli price 'window' candles madhye sarvat kami ahe
        if lows[i] == min(lows[i - window : i + window + 1]):
            raw_supports.append(lows[i])
            
    current_price = closes[-1]
    
    # 2. Levels Cluster karne (ekmekanna javal aslelya levels cha zone banvane)
    def cluster_levels(levels):
        if not levels:
            return []
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]
        
        for price in levels[1:]:
            # Jar price pashil level chya threshold madhye asel tar tya cluster madhe joda
            if (price - np.mean(current_cluster)) / np.mean(current_cluster) <= cluster_threshold:
                current_cluster.append(price)
            else:
                clusters.append(current_cluster)
                current_cluster = [price]
        clusters.append(current_cluster)
        
        # Pratyek cluster chi mean price ani touch count kadhane
        consolidated = []
        for c in clusters:
            level_price = round(float(np.mean(c)), 2)
            touch_count = len(c)
            consolidated.append((level_price, touch_count))
            
        return consolidated

    res_clustered = cluster_levels(raw_resistances)
    supp_clustered = cluster_levels(raw_supports)
    
    # Fakt Current Price chya varchya (Resistances) ani khalcya (Supports) filter karne
    valid_resistances = [r for r in res_clustered if r[0] > current_price]
    valid_supports = [s for s in supp_clustered if s[0] < current_price]
    
    # Sort: Current price chya sarvat javal aslelya levels
    valid_resistances.sort(key=lambda x: x[0])             # Ascending (javalcha resistance aadhi)
    valid_supports.sort(key=lambda x: x[0], reverse=True)  # Descending (javalcha support aadhi)
    
    return current_price, valid_supports, valid_resistances

def run_analysis(ticker="KOTAKBANK.NS", period="6mo", interval="1d"):
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    if data.empty or len(data) < 30:
        print("Data uplabdha nahi.")
        return
        
    ltp, supports, resistances = calculate_robust_sr(data, window=5)
    
    print("=" * 55)
    print(f"📊 STOCK: {ticker} | CURRENT PRICE (LTP): ₹{round(float(ltp), 2)}")
    print("=" * 55)
    
    print("\n🔻 KEY SUPPORT LEVELS (खालचे मजबूत आधार):")
    if supports:
        for idx, (price, count) in enumerate(supports[:4], 1):
            strength = "⭐⭐⭐ (Strong)" if count >= 3 else ("⭐⭐ (Moderate)" if count == 2 else "⭐ (Weak)")
            print(f"  S{idx} : ₹{price:<8} | Touches: {count} वेळा टेस्ट | Strength: {strength}")
    else:
        print("  Konthahi majboot support sapadla nahi.")
        
    print("\n🔺 KEY RESISTANCE LEVELS (वरचे अडथळे):")
    if resistances:
        for idx, (price, count) in enumerate(resistances[:4], 1):
            strength = "⭐⭐⭐ (Strong)" if count >= 3 else ("⭐⭐ (Moderate)" if count == 2 else "⭐ (Weak)")
            print(f"  R{idx} : ₹{price:<8} | Touches: {count} वेळा टेस्ट | Strength: {strength}")
    else:
        print("  Konthahi majboot resistance sapadla nahi.")
    print("=" * 55)

# Run
if __name__ == "__main__":
    run_analysis("KOTAKBANK.NS", period="6mo", interval="1d")
