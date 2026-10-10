import numpy as np

def find_pivots(df, left_bars=3, right_bars=3):
    """
    खरे Swing High (Resistance) आणि Swing Low (Support) शोधणे
    जिथे डाव्या आणि उजव्या कॅन्डल्सपेक्षा मधली कॅन्डल जास्त उंच/खालची असते.
    """
    df = df.copy()
    df['is_swing_high'] = False
    df['is_swing_low'] = False

    for i in range(left_bars, len(df) - right_bars):
        high_window = df['High'].iloc[i - left_bars : i + right_bars + 1]
        low_window = df['Low'].iloc[i - left_bars : i + right_bars + 1]

        if df['High'].iloc[i] == high_window.max():
            df.iat[i, df.columns.get_loc('is_swing_high')] = True

        if df['Low'].iloc[i] == low_window.min():
            df.iat[i, df.columns.get_loc('is_swing_low')] = True

    swing_highs = df[df['is_swing_high']]['High'].tolist()
    swing_lows = df[df['is_swing_low']]['Low'].tolist()

    # सर्वात अलीकडील 2 महत्त्वाचे लेव्हल्स घेणे
    valid_res = swing_highs[-1] if len(swing_highs) > 0 else df['High'].max()
    valid_sup = swing_lows[-1] if len(swing_lows) > 0 else df['Low'].min()

    return valid_sup, valid_res

def scan_and_match(symbol_list, interval, period, window, tol, mode):
    matched_results = []
    tickers = [f"{s}.NS" for s in symbol_list]

    raw_data = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        group_by='ticker',
        threads=True,
        progress=False
    )

    for sym in symbol_list:
        ticker = f"{sym}.NS"
        try:
            if ticker not in raw_data.columns.levels[0]:
                continue
            df = raw_data[ticker].dropna()
            if len(df) < 20:
                continue

            curr_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]

            curr_close = curr_candle['Close']
            curr_high = curr_candle['High']
            curr_low = curr_candle['Low']

            # 1. Classical Pivot Points (Daily S1/R1)
            p_high, p_low, p_close = prev_candle['High'], prev_candle['Low'], prev_candle['Close']
            pivot = (p_high + p_low + p_close) / 3
            r1 = (2 * pivot) - p_low
            s1 = (2 * pivot) - p_high

            # 2. अस्सल Swing Support आणि Resistance (Fractal Method)
            swing_sup, swing_res = find_pivots(df, left_bars=2, right_bars=2)

            levels = {
                "Swing Support": swing_sup,
                "Support 1 (S1)": s1,
                "Swing Resistance": swing_res,
                "Resistance 1 (R1)": r1
            }

            for level_name, level_price in levels.items():
                is_matched = False
                match_status = ""
                
                # Close प्राईसचा लेव्हलपासून फरक
                close_diff_pct = abs(curr_close - level_price) / level_price * 100
                
                # High/Low चा लेव्हलपासून थेट फरक (Exact Touch तपासण्यासाठी)
                low_diff_pct = abs(curr_low - level_price) / level_price * 100
                high_diff_pct = abs(curr_high - level_price) / level_price * 100

                if "Support" in level_name:
                    # कॅन्डलच्या Low ने सपोर्टला अचूक स्पर्श केला (0.25% टॉलरन्सच्या आत) आणि किंमत तिथून वर Close झाली
                    if low_diff_pct <= 0.25 and curr_close >= curr_low:
                        is_matched = True
                        match_status = f"🟢 Low Tested Support ({low_diff_pct:.2f}%)"
                    elif mode != "Exact Level Match" and close_diff_pct <= tol:
                        is_matched = True
                        match_status = f"🟢 Near Support ({close_diff_pct:.2f}%)"

                elif "Resistance" in level_name:
                    # कॅन्डलच्या High ने रेझिस्टन्सला अचूक स्पर्श केला (0.25% टॉलरन्सच्या आत) आणि किंमत तिथून खाली आली
                    if high_diff_pct <= 0.25 and curr_close <= curr_high:
                        is_matched = True
                        match_status = f"🔴 High Tested Resistance ({high_diff_pct:.2f}%)"
                    elif mode != "Exact Level Match" and close_diff_pct <= tol:
                        is_matched = True
                        match_status = f"🔴 Near Resistance ({close_diff_pct:.2f}%)"

                if is_matched:
                    diff_val = curr_close - level_price
                    matched_results.append({
                        "Symbol": sym,
                        "LTP (₹)": round(curr_close, 2),
                        "Matched Level": level_name,
                        "Level Price (₹)": round(level_price, 2),
                        "फरक (₹)": round(diff_val, 2),
                        "फरक (%)": round(close_diff_pct, 2),
                        "Status": match_status,
                        "S1": round(s1, 2),
                        "R1": round(r1, 2),
                        "Swing Low": round(swing_sup, 2),
                        "Swing High": round(swing_res, 2)
                    })
                    break
        except Exception:
            continue

    return pd.DataFrame(matched_results)
