import streamlit as st
import pandas as pd
import pyotp
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from SmartApi import SmartConnect
import plotly.graph_objects as go

st.set_page_config(page_title="NSE 200 Real-Time S&R Engine", layout="wide")

st.title("⚡ NSE 200 Live Background S&R Scanner")
st.caption("बॅकग्राउंडमध्ये सतत अपडेट होणारा रिअल-टाइम ब्रेकआऊट व ब्रेकडाऊन डॅशबोर्ड")

# --- १. युझर क्रेडेंशियल्स आणि सेटिंग्ज ---
st.sidebar.header("🔐 Angel One लॉगिन")
API_KEY = st.sidebar.text_input("API Key", value="YOUR_API_KEY", type="password")
CLIENT_CODE = st.sidebar.text_input("Client Code", value="YOUR_CLIENT_CODE")
MPIN = st.sidebar.text_input("MPIN", value="YOUR_MPIN", type="password")
TOTP_SECRET = st.sidebar.text_input("TOTP Secret Key", value="YOUR_TOTP_KEY", type="password")

TIMEFRAME_MAP = {
    "5 Minutes (Intraday)": {"interval": "FIVE_MINUTE", "days": 2},
    "15 Minutes": {"interval": "FIFTEEN_MINUTE", "days": 5},
    "1 Hour (Swing)": {"interval": "ONE_HOUR", "days": 15},
    "1 Day (Daily)": {"interval": "ONE_DAY", "days": 60}
}

selected_tf = st.sidebar.selectbox("Timeframe निवडा:", list(TIMEFRAME_MAP.keys()), index=2)
tf_config = TIMEFRAME_MAP[selected_tf]

# बॅकग्राउंड स्कॅन इंटरव्हल (दर किती सेकंदांनी रि-स्कॅन व्हावे)
scan_interval_sec = st.sidebar.slider("Background Scan Interval (सेकंद):", min_value=15, max_value=180, value=30, step=15)

# --- २. Nifty 200 शेअर्सची यादी ---
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

# --- ३. Angel One Scrip Master टोकन्स ---
@st.cache_data(ttl=86400)
def get_nifty200_tokens(symbols):
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        nse_map = {
            item['symbol'].replace('-EQ', ''): str(item['token'])
            for item in data 
            if item.get('exch_seg') == 'NSE' and item.get('symbol', '').endswith('-EQ')
        }
        return {sym: nse_map[sym] for sym in symbols if sym in nse_map}
    except Exception:
        return {}

# --- ४. स्मार्ट सेशन इनिशियलायझेशन ---
@st.cache_resource
def get_smart_session(api_key, client_code, mpin, totp_key):
    try:
        smart_api = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_key).now()
        data = smart_api.generateSession(client_code, mpin, totp)
        if data['status']:
            return smart_api
        return None
    except Exception:
        return None

# --- ५. सिंगल स्टॉक स्कॅन लॉजिक ---
def scan_single_stock(smart_api, sym, tok, interval, days):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        param = {
            "exchange": "NSE",
            "symboltoken": str(tok),
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d 09:15"),
            "todate": to_date.strftime("%Y-%m-%d 15:30")
        }
        res = smart_api.getCandleData(param)
        if not res or 'data' not in res or not res['data'] or len(res['data']) < 3:
            return None

        data = res['data']
        prev_candle = data[-2]
        curr_candle = data[-1]

        last_high = float(prev_candle[2])  # High
        last_low = float(prev_candle[3])   # Low
        prev_close = float(prev_candle[4]) # Close
        ltp = float(curr_candle[4])        # LTP

        # स्टेटस तपासणे
        if ltp > last_high:
            status = "🚀 Resistance Breakout"
        elif ltp < last_low:
            status = "🔻 Support Breakdown"
        else:
            return None  # Rangebound असल्यास थेट वगळा (फक्त ब्रेकआऊट सेव्ह करा)

        pct_chg = ((ltp - prev_close) / prev_close) * 100
        candle_time = prev_candle[0]

        return {
            "Symbol": sym,
            "LTP (₹)": round(ltp, 2),
            "Change (%)": round(pct_chg, 2),
            "Last High (Res)": round(last_high, 2),
            "Last Low (Sup)": round(last_low, 2),
            "Candle Time": candle_time,
            "Status": status,
            "Updated At": datetime.now().strftime("%H:%M:%S")
        }
    except Exception:
        return None

# --- ६. ग्लोबल स्टेट आणि बॅकग्राउंड स्कॅनर थ्रेड ---
if "background_data" not in st.session_state:
    st.session_state["background_data"] = pd.DataFrame()
if "last_scan_time" not in st.session_state:
    st.session_state["last_scan_time"] = "अजून सुरू नाही"
if "is_worker_running" not in st.session_state:
    st.session_state["is_worker_running"] = False

token_map = get_nifty200_tokens(NIFTY_200_SYMBOLS)
api_client = None
if API_KEY != "YOUR_API_KEY" and CLIENT_CODE != "YOUR_CLIENT_CODE":
    api_client = get_smart_session(API_KEY, CLIENT_CODE, MPIN, TOTP_SECRET)

def fast_parallel_scan():
    """ThreadPool वापरून अतिजलद स्कॅन करणे"""
    if not api_client or not token_map:
        return
    
    active_records = []
    # 8 Threads मुळे २०० शेअर्स काही सेकंदांत पूर्ण होतात
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(scan_single_stock, api_client, sym, tok, tf_config["interval"], tf_config["days"])
            for sym, tok in token_map.items()
        ]
        for f in futures:
            res = f.result()
            if res:
                active_records.append(res)

    if active_records:
        st.session_state["background_data"] = pd.DataFrame(active_records)
    else:
        st.session_state["background_data"] = pd.DataFrame(columns=["Symbol", "LTP (₹)", "Change (%)", "Last High (Res)", "Last Low (Sup)", "Status", "Updated At"])
    
    st.session_state["last_scan_time"] = datetime.now().strftime("%H:%M:%S")

# --- ७. मुख्य डिस्प्ले आणि ऑटो-रिफ्रेश ---
col_ctrl1, col_ctrl2 = st.columns([2, 1])
with col_ctrl1:
    st.write(f"🕒 **शेवटचे बॅकग्राउंड अपडेट:** `{st.session_state['last_scan_time']}`")
with col_ctrl2:
    auto_refresh = st.toggle("🔄 Auto Refresh (सतत चालू ठेवा)", value=True)

# जर डेटा अजून नसेल किंवा मॅन्युअल रिफ्रेश हवा असेल तर लगेच स्कॅन करा
if st.session_state["background_data"].empty and api_client:
    with st.spinner("बॅकग्राउंड इंजिन सुरू होत आहे... २०० शेअर्स स्कॅन होत आहेत..."):
        fast_parallel_scan()

df_live = st.session_state["background_data"]

if not df_live.empty:
    breakouts = df_live[df_live['Status'] == "🚀 Resistance Breakout"]
    breakdowns = df_live[df_live['Status'] == "🔻 Support Breakdown"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Resistance Breakouts", len(breakouts))
    m2.metric("Support Breakdowns", len(breakdowns))
    m3.metric("एकूण ॲक्शन शेअर्स", len(df_live))

    tab_res, tab_sup = st.tabs(["🚀 Resistance Breakout शेअर्स", "🔻 Support Breakdown शेअर्स"])

    with tab_res:
        if not breakouts.empty:
            st.dataframe(breakouts[["Symbol", "LTP (₹)", "Change (%)", "Last High (Res)", "Status", "Updated At"]], use_container_width=True)
        else:
            st.info("सध्या कोणताही Resistance Breakout झालेला नाही.")

    with tab_sup:
        if not breakdowns.empty:
            st.dataframe(breakdowns[["Symbol", "LTP (₹)", "Change (%)", "Last Low (Sup)", "Status", "Updated At"]], use_container_width=True)
        else:
            st.info("सध्या कोणताही Support Breakdown झालेला नाही.")
else:
    st.warning("कृपया Angel One चे योग्य Credentials भरा आणि स्कॅन सुरू करा.")

# ऑटोमॅटिक बॅकग्राउंड रिफ्रेश लूप (UI ब्लॉक न करता ठरावीक वेळेनंतर अपडेट)
if auto_refresh and api_client:
    time.sleep(scan_interval_sec)
    fast_parallel_scan()
    st.rerun()
