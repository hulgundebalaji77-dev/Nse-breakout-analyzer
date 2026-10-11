import streamlit as st
import pandas as pd
import pyotp
import requests
from SmartApi import SmartConnect
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="NSE 200 S&R Screener", layout="wide")

st.title("🎯 Angel One SmartAPI - NSE 200 Auto Filter S&R Screener")

# --- 1. Angel One Credentials Configuration ---
st.sidebar.header("🔐 SmartAPI Login Details")
API_KEY = st.sidebar.text_input("API Key", value="YOUR_API_KEY", type="password")
CLIENT_CODE = st.sidebar.text_input("Client Code", value="YOUR_CLIENT_CODE")
MPIN = st.sidebar.text_input("MPIN", value="YOUR_MPIN", type="password")
TOTP_SECRET = st.sidebar.text_input("TOTP Secret Key", value="YOUR_TOTP_KEY", type="password")

# --- 2. SmartAPI Timeframe Mapping ---
TIMEFRAME_MAP = {
    "5 Minutes (Intraday)": {"interval": "FIVE_MINUTE", "days": 2},
    "15 Minutes": {"interval": "FIFTEEN_MINUTE", "days": 5},
    "1 Hour (Swing)": {"interval": "ONE_HOUR", "days": 15},
    "1 Day (Daily Swing)": {"interval": "ONE_DAY", "days": 60}
}

selected_tf = st.sidebar.selectbox("Select Timeframe:", list(TIMEFRAME_MAP.keys()), index=2)
tf_config = TIMEFRAME_MAP[selected_tf]

# --- 3. Nifty 200 सर्व शेअर्सची यादी ---
NIFTY_200_SYMBOLS = [
    "ABB", "ACC", "APLAPOLLO", "AUBANK", "ADANIENSOL", "ADANIENT", "ADANIGREEN", 
    "ADANIPORTS", "ADANIPOWER", "ATGL", "ABCAPITAL", "ABFRL", "ALKEM", "AMBUJACEM", 
    "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "AUROPHARMA", 
    "AXISBANK", "BSOFT", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BAJAJHLDNG", 
    "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "BERGEPAINT", "BEL", 
    "BHARATFORG", "BHEL", "BPCL", "BHARTIARTL", "BIOCON", "BOSCHLTD", "BRITANNIA", 
    "CGPOWER", "CANBK", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", 
    "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUMMINSIND", "DLF", "DABUR", 
    "DALBHARAT", "DEEPAKNTR", "DELHIVERY", "DIVISLAB", "DIXON", "LALPATHLAB", 
    "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "NYKAA", "FEDERALBNK", "FACT", 
    "FORTIS", "GAIL", "GMRINFRA", "GLENMARK", "GODREJCP", "GODREJPROP", "GRANULES", 
    "GRASIM", "GUJGASLTD", "HAL", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", 
    "HAVELLS", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", 
    "HUDCO", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "IPCALAB", "IRB", 
    "ITC", "INDIAMART", "INDIANB", "IEX", "IOC", "IRCTC", "IRFC", "IREDA", "IGL", 
    "INDUSTOWER", "INDUSINDBK", "NAUKRI", "INFY", "INDIGO", "JINDALSTEL", "JIOFIN", 
    "JSWENERGY", "JSWINFRA", "JSWSTEEL", "JUBLFOOD", "KALYANKJIL", "KEI", "KOTAKBANK", 
    "LTF", "LT", "LTIM", "LICHSGFIN", "LICI", "LUPIN", "MRF", "M&MFIN", "M&M", 
    "MANAPPURAM", "MARICO", "MARUTI", "MAXHEALTH", "MAZDOCK", "METROPOLIS", "MFSL", 
    "MPHASIS", "MUTHOOTFIN", "NATCOPHARM", "NBCC", "NCC", "NHPC", "NMDC", "NTPC", 
    "NATIONALUM", "NAVINFLUOR", "NESTLEIND", "NLCINDIA", "OBEROIRLTY", "ONGC", 
    "OIL", "PAYTM", "OFSS", "PAGEIND", "PATANJALI", "PERSISTENT", "PETRONET", 
    "PFIZER", "PHOENIXLTD", "PIDILITIND", "PIIND", "PNB", "POLICYBZR", "POLYCAB", 
    "POONAWALLA", "PFC", "POWERGRID", "PRESTIGE", "RVNL", "RAILTEL", "RBLBANK", 
    "REC", "RELIANCE", "SBICARD", "SBILIFE", "SJVN", "SRF", "MOTHERSON", "SAIL", 
    "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SOLARINDS", "SONACOMS", "SBIN", "SUNPHARMA", 
    "SUNTV", "SUPREMEIND", "SUZLON", "SYNGENE", "TATACHEM", "TATACOMM", "TCS", 
    "TATACONSUM", "TATAELXSI", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TATATECH", 
    "TECHM", "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TIINDIA", "UPL", 
    "ULTRACEMCO", "UNIONBANK", "UBL", "UNITDSPR", "VBL", "VEDL", "VOLTAS", 
    "WIPRO", "YESBANK", "ZOMATO", "ZYDUSLIFE"
]

# --- 4. Angel One Master Tokens ऑटोमॅटिक लोड करणे ---
@st.cache_data(ttl=86400)
def get_nifty200_tokens(symbols_list):
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        nse_eq_map = {
            item['symbol'].replace('-EQ', ''): str(item['token'])
            for item in data 
            if item.get('exch_seg') == 'NSE' and item.get('symbol', '').endswith('-EQ')
        }
        token_dict = {sym: nse_eq_map[sym] for sym in symbols_list if sym in nse_eq_map}
        return token_dict
    except Exception:
        return {}

# --- 5. Angel One Login Session ---
@st.cache_resource
def get_smart_session(api_key, client_code, mpin, totp_key):
    try:
        smart_api = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_key).now()
        data = smart_api.generateSession(client_code, mpin, totp)
        if data['status']:
            return smart_api
        return None
    except Exception as e:
        st.sidebar.error(f"Login Error: {e}")
        return None

# --- 6. Live Candle Data आणणे ---
def fetch_angel_candles(smart_api, token, interval, days_back):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)

        historic_param = {
            "exchange": "NSE",
            "symboltoken": str(token),
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d 09:15"),
            "todate": to_date.strftime("%Y-%m-%d 15:30")
        }

        res = smart_api.getCandleData(historic_param)
        if not res or 'data' not in res or not res['data']:
            return None

        df = pd.DataFrame(res['data'], columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = df[col].astype(float)

        return df
    except Exception:
        return None

# --- 7. Breakout Logic ---
def check_angel_breakout(df, symbol):
    if df is None or len(df) < 3:
        return None

    prev_candle = df.iloc[-2]
    curr_candle = df.iloc[-1]

    last_high = float(prev_candle['High'])
    last_low = float(prev_candle['Low'])
    ltp = float(curr_candle['Close'])

    status = "Inside Range"
    if ltp > last_high:
        status = "🚀 Resistance Breakout"
    elif ltp < last_low:
        status = "🔻 Support Breakdown"

    pct_chg = ((ltp - float(prev_candle['Close'])) / float(prev_candle['Close'])) * 100

    return {
        "Symbol": symbol,
        "LTP (₹)": round(ltp, 2),
        "Candle Chg (%)": round(pct_chg, 2),
        "Last High (Res)": round(last_high, 2),
        "Last Low (Sup)": round(last_low, 2),
        "Candle Time": prev_candle['Datetime'].strftime("%d-%b %H:%M"),
        "Status": status
    }

# --- 8. Execution & Interface ---
api_client = None
if API_KEY != "YOUR_API_KEY" and CLIENT_CODE != "YOUR_CLIENT_CODE":
    api_client = get_smart_session(API_KEY, CLIENT_CODE, MPIN, TOTP_SECRET)

token_map = get_nifty200_tokens(NIFTY_200_SYMBOLS)

if st.button(f"🔍 Scan All Nifty 200 Stocks ({selected_tf})"):
    if not api_client:
        st.error("कृपया sidebar मध्ये अचूक Angel One Credentials भरा.")
    elif not token_map:
        st.error("Angel One Scrip Master टोकन्स लोड करता आले नाहीत. इंटरनेट कनेक्शन तपासा.")
    else:
        results = []
        prog = st.progress(0)
        stat = st.empty()
        total_stocks = len(token_map)

        for idx, (sym, tok) in enumerate(token_map.items()):
            stat.text(f"Scanning {sym} ({idx+1}/{total_stocks})...")
            df_stock = fetch_angel_candles(api_client, tok, tf_config["interval"], tf_config["days"])
            info = check_angel_breakout(df_stock, sym)
            if info:
                results.append(info)
            prog.progress((idx + 1) / total_stocks)

        stat.empty()
        prog.empty()

        if results:
            st.session_state["angel_results"] = pd.DataFrame(results)

# --- 9. ऑटोमॅटिक फिल्टर झालेले टेबल्स (Resistance व Support) ---
if "angel_results" in st.session_state:
    res_df = st.session_state["angel_results"]
    
    # थेट फिल्टर केलेले डेटाफ्रेम्स
    breakouts = res_df[res_df['Status'] == "🚀 Resistance Breakout"]
    breakdowns = res_df[res_df['Status'] == "🔻 Support Breakdown"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Resistance Breakouts", len(breakouts
