# Multi-index columns flat karnyasathi (yfinance download nantar he add kara):
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# ---------------------------------------------------------
# Support ani Resistance calculate karnyasathi ha safe loop vapara:
# ---------------------------------------------------------
highs = []
lows = []
window = 5  # Left and right bars count

for i in range(window, len(df) - window):
    # Current bar che values (.item() kinva float conversion vapara)
    current_high = float(df['High'].iloc[i])
    current_low = float(df['Low'].iloc[i])
    
    # Left ani Right bars che maximum / minimum kadha
    prev_highs = df['High'].iloc[i - window : i + window + 1]
    prev_lows = df['Low'].iloc[i - window : i + window + 1]
    
    # Swing High (Resistance) check
    if current_high == float(prev_highs.max()):
        highs.append(current_high)
        
    # Swing Low (Support Pivot) check
    if current_low == float(prev_lows.min()):
        lows.append(current_low)
