import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# -------------------------------------------------------------------
# १. पेज कॉन्फिगरेशन
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Nifty 200 Multi-Timeframe Scanner",
    layout="wide",
    page_icon="📈",
)
st.title("📊 Nifty 200 Multi-Timeframe Camarilla & EMA Scanner")

# -------------------------------------------------------------------
# २. टेलिग्राम अलर्ट फंक्शन
# -------------------------------------------------------------------
def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception:
        return False


# -------------------------------------------------------------------
# ३. साइडबार सेटिंग्स (Timeframe, Telegram & Filters)
# -------------------------------------------------------------------
st.sidebar.header("⚙️ Timeframe & Settings")

# सर्व मुख्य टाइमफ्रेम्सचा पर्याय
timeframe_options = {
    "15 Minute (Intraday)": {"interval": "15m", "period": "5d"},
    "1 Hour (Intraday / Positional)": {"interval": "60m", "period": "1mo"},
    "1 Day (Daily Swing)": {"interval": "1d", "period": "1y"},
    "1 Week (Weekly Long-term)": {"interval": "1wk", "period": "2y"},
}

selected_tf_name = st.sidebar.selectbox(
    "⏱️ Select Timeframe:", list(timeframe_options.keys()), index=2
)
selected_config = timeframe_options[selected_tf_name]

st.sidebar.markdown("---")
st.sidebar.header("📲 Telegram Alerts (ऐच्छिक)")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID")

scan_button = st.sidebar.button("🚀 Run Live Scan")

# -------------------------------------------------------------------
# ४. Nifty 200 स्टॉक लिस्ट मिळवणे
# -------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_nifty200_symbols():
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    df_indices = pd.read_csv(pd.io.common.BytesIO(res.content))
    return [f"{s}.NS" for s in df_indices["Symbol"].tolist()]


# -------------------------------------------------------------------
# ५. निवडलेल्या टाइमफ्रेमसाठी स्कॅनिंग लॉजिक
# -------------------------------------------------------------------
def run_scanner(tickers, interval, period):
    data = yf.download(
        tickers,
        period=period,
        interval=interval,
        group_by="ticker",
        threads=True,
    )
    records = []

    for sym in tickers:
        try:
            df = data[sym].dropna()
            if len(df) < 5:
                continue

            # मागील कँडल आणि चालू भाव
            prev_high = float(df["High"].iloc[-2])
            prev_low = float(df["Low"].iloc[-2])
            prev_close = float(df["Close"].iloc[-2])
            ltp = float(df["Close"].iloc[-1])

            # Dynamic Moving Averages (डेटा पुरेसा असल्यास)
            ema_20 = (
                float(df["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
                if len(df) >= 20
                else 0.0
            )
            ema_50 = (
                float(df["Close"].ewm(span=50, adjust=False).mean().iloc[-1])
                if len(df) >= 50
                else 0.0
            )

            # Camarilla Levels (मागील कँडलच्या रेंजवरून)
            rng = prev_high - prev_low
            h4 = prev_close + (rng * (1.1 / 2))
            h3 = prev_close + (rng * (1.1 / 4))
            l3 = prev_close - (rng * (1.1 / 4))
            l4 = prev_close - (rng * (1.1 / 2))

            # Pivot Point
            pivot = (prev_high + prev_low + prev_close) / 3

            # सिग्नल्स
            if ltp > h4:
                signal = "Bullish Breakout (Above H4)"
            elif ltp < l4:
                signal = "Bearish Breakdown (Below L4)"
            elif h3 <= ltp <= h4:
                signal = "Resistance Zone (H3-H4)"
            elif l4 <= ltp <= l3:
                signal = "Support Zone (L3-L4)"
            else:
                signal = "Normal Range"

            records.append(
                {
                    "Stock": sym.replace(".NS", ""),
                    "LTP": round(ltp, 2),
                    "H4_Breakout": round(h4, 2),
                    "H3_Short": round(h3, 2),
                    "L3_Buy": round(l3, 2),
                    "L4_Breakdown": round(l4, 2),
                    "Pivot": round(pivot, 2),
                    "20_EMA": round(ema_20, 2) if ema_20 else "N/A",
                    "50_EMA": round(ema_50, 2) if ema_50 else "N/A",
                    "Signal": signal,
                }
            )
        except Exception:
            continue

    return pd.DataFrame(records)


# -------------------------------------------------------------------
# ६. स्क्रीनवर निकाल दाखवणे
# -------------------------------------------------------------------
if scan_button:
    with st.spinner(
        f"Nifty 200 शेअर्स [{selected_tf_name}] टाइमफ्रेमवर स्कॅन होत आहेत..."
    ):
        tickers = get_nifty200_symbols()
        scan_df = run_scanner(
            tickers, selected_config["interval"], selected_config["period"]
        )

    if not scan_df.empty:
        bullish_df = scan_df[
            scan_df["Signal"] == "Bullish Breakout (Above H4)"
        ]
        bearish_df = scan_df[
            scan_df["Signal"] == "Bearish Breakdown (Below L4)"
        ]

        # Top Summary Metrics
        st.subheader(f"📌 Timeframe: {selected_tf_name}")
        c1, c2, c3 = st.columns(3)
        c1.metric("एकूण स्टॉक्स", len(scan_df))
        c2.metric("🟢 बुलिश ब्रेकआउट्स (H4)", len(bullish_df))
        c3.metric("🔴 बेअरिश ब्रेकडाउन्स (L4)", len(bearish_df))

        # फिल्टरिंग पर्याय
        selected_signal = st.selectbox(
            "सिग्नलनुसार फिल्टर करा:",
            [
                "All",
                "Bullish Breakout (Above H4)",
                "Bearish Breakdown (Below L4)",
                "Resistance Zone (H3-H4)",
                "Support Zone (L3-L4)",
                "Normal Range",
            ],
        )

        display_df = (
            scan_df
            if selected_signal == "All"
            else scan_df[scan_df["Signal"] == selected_signal]
        )
        st.dataframe(display_df, use_container_width=True)

        # Telegram वर मेसेज पाठवणे
        if bot_token and chat_id and (len(bullish_df) > 0 or len(bearish_df) > 0):
            msg = f"🚨 Nifty 200 Alert [{selected_tf_name}] 🚨\n\n"

            if not bullish_df.empty:
                msg += "🟢 Bullish Breakouts (Above H4):\n"
                for _, row in bullish_df.head(15).iterrows():  # Top 15 stocks
                    msg += f"• {row['Stock']}: ₹{row['LTP']} (H4: ₹{row['H4_Breakout']})\n"
                msg += "\n"

            if not bearish_df.empty:
                msg += "🔴 Bearish Breakdowns (Below L4):\n"
                for _, row in bearish_df.head(15).iterrows():
                    msg += f"• {row['Stock']}: ₹{row['LTP']} (L4: ₹{row['L4_Breakdown']})\n"

            success = send_telegram_alert(bot_token, chat_id, msg)
            if success:
                st.success("✅ Telegram वर अलर्ट पाठवला गेला!")
            else:
                st.error("❌ Telegram अलर्ट अयशस्वी. टोकन आणि चॅट आयडी तपासा.")
    else:
        st.error("डेटा खेचता आला नाही. इंटरनेट कनेक्शन तपासा.")
else:
    st.info(
        "👈 डाव्या बाजूला *Timeframe* निवडा आणि *'Run Live Scan'* बटनावर क्लिक करा."
    )
