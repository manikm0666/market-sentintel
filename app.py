import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
from datetime import datetime, timedelta
from twelvedata import TDClient

# --- 1. CONFIGURATION & STYLING ---
API_KEY = "YOUR_FREE_API_KEY" 

st.set_page_config(page_title="Market Sentinel Pro", layout="wide", initial_sidebar_state="expanded")

# Restoring your original "Dark Terminal" CSS 
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(128,128,128,0.1);
        padding: 15px; border-radius: 12px;
    }
    .proj-text { font-size: 24px; font-weight: bold; text-shadow: 0 0 10px rgba(0,255,65,0.4); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GLOBAL UTILITIES (Restored from old code)  ---
def format_val(num):
    if num is None or num == "N/A": return "N/A"
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B', 'T']:
            if abs(num) < 1000.0: return f"{num:3.1f}{unit}"
            num /= 1000.0
        return f"{num:.1f}P"
    except: return "N/A"

@st.cache_data(ttl=60)
def fetch_market_data(ticker, interval):
    try:
        td = TDClient(apikey=API_KEY)
        ts = td.time_series(symbol=ticker, interval=interval, outputsize=100, order="ASC").as_pandas()
        quote = td.quote(symbol=ticker).as_json()
        return ts, quote
    except Exception as e:
        return None, None

# --- 3. SIDEBAR & WATCHLIST (Restored functionality)  ---
st.sidebar.title("💠 SENTINEL PRO")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# Persistent Ticker State
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

time_map = {"1D": "1min", "5D": "5min", "1M": "1h", "1Y": "1day"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=0)

st.sidebar.markdown("---")
if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]

if st.sidebar.button("🗑️ Clear Watchlist"):
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]
    st.rerun()

for fav in st.session_state.favorites:
    if st.sidebar.button(f"★ {fav}", key=f"side_{fav}", use_container_width=True):
        st.session_state.current_ticker = fav
        st.rerun()

# --- 4. MAIN ENGINE ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: Educational purposes only.")

df, info = fetch_market_data(TICKER, time_map[selected_label])

if df is not None and not df.empty:
    # 1. Restore Download Button 
    st.sidebar.markdown("---")
    st.sidebar.download_button("📥 DOWNLOAD CSV", df.to_csv().encode('utf-8'), f"{TICKER}.csv", use_container_width=True)

    # 2. Header & Star Toggle 
    c_title, c_star = st.columns([0.85, 0.15])
    c_title.title(f"{info.get('name', TICKER)} ({TICKER})")
    
    is_fav = TICKER in st.session_state.favorites
    if c_star.button("★" if is_fav else "☆", use_container_width=True, key="star_main"):
        if is_fav: st.session_state.favorites.remove(TICKER)
        else: st.session_state.favorites.append(TICKER)
        st.rerun()

    # 3. Projection & Metrics 
    y = df['close'].values.astype(float)
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    f_steps = int(len(x) * 0.15)
    y_proj = slope * (np.arange(len(x), len(x) + f_steps)) + intercept
    
    st.markdown(f"<div class='proj-text'>🔮 AI PROJECTION: <span style='color:#00FF41;'>${y_proj[-1]:.2f}</span></div>", unsafe_allow_html=True)

    m1, m2 = st.columns(2); m3, m4 = st.columns(2)
    m1.metric("Current Price", f"${y[-1]:.2f}")
    m2.metric("Trend Velocity", f"{slope:+.4f}", delta=f"{slope:.4f}")
    m3.metric("Market Cap", format_val(info.get('market_cap')))
    m4.metric("52W High", f"${info.get('fifty_two_week_high', 'N/A')}")

    # 4. Chart Aesthetic 
    fig = go.Figure()
    # Actual Data
    fig.add_trace(go.Scatter(x=df.index, y=df['close'], name="Actual", 
                             line=dict(color="#00FF41" if y[-1] >= y[0] else "#FF3131", width=3)))
    
    # Projection Path
    last_date = df.index[-1]
    f_dates = [last_date + (df.index[-1] - df.index[-2]) * i for i in range(1, f_steps + 1)]
    fig.add_trace(go.Scatter(x=f_dates, y=y_proj, name="Path", line=dict(color="#00FF41", width=2, dash='dot')))
    
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"📡 API Limit or Invalid Symbol. (Twelve Data daily limit: 800)")