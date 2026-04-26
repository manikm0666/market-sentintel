import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
import requests
from twelvedata import TDClient

# --- CONFIGURATION ---
TD_KEY = "79c371cc5cf04adb94d7038c449d2c01"
NEWS_KEY = "LStl2d8iIgGGdU1FRuGPsIbyJWPRgke6EyLVYPFF"

st.set_page_config(page_title="Sentinel Pro", layout="wide")

# RESTORED: Your Original Terminal Aesthetic
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 15px; border: 1px solid #30363D; }
    .proj-glow { font-size: 26px; font-weight: bold; text-shadow: 0 0 10px #00FF41; color: #00FF41; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINES ---
@st.cache_data(ttl=60)
def fetch_all_market(ticker, interval):
    try:
        td = TDClient(apikey=TD_KEY)
        df = td.time_series(symbol=ticker, interval=interval, outputsize=100, order="ASC").as_pandas()
        quote = td.quote(symbol=ticker).as_json()
        return df, quote
    except: return None, None

@st.cache_data(ttl=600)
def fetch_news(ticker):
    url = f"https://api.marketaux.com/v1/news/all?symbols={ticker}&filter_entities=true&limit=3&api_token={NEWS_KEY}"
    try: return requests.get(url).json().get('data', [])
    except: return []

# --- SIDEBAR & WATCHLIST ---
st_autorefresh(interval=60 * 1000, key="refresh")
if 'favs' not in st.session_state: st.session_state.favs = ["NVDA", "TSLA", "BTC/USD"]

st.sidebar.title("💠 SENTINEL PRO")
TICKER = st.sidebar.text_input("SEARCH", value=st.session_state.get('curr', 'AAPL')).upper()
st.session_state.curr = TICKER

t_map = {"1D": "1min", "1M": "1h", "1Y": "1day"}
sel_t = st.sidebar.selectbox("TIMEFRAME", list(t_map.keys()))

# FEATURE: Sidebar Watchlist
for f in st.session_state.favs:
    if st.sidebar.button(f"★ {f}", use_container_width=True):
        st.session_state.curr = f
        st.rerun()

# --- MAIN DASHBOARD ---
df, info = fetch_all_market(TICKER, t_map[sel_t])

if df is not None and not df.empty:
    # FEATURE: Download CSV
    st.sidebar.download_button("📥 DOWNLOAD DATA", df.to_csv(), f"{TICKER}.csv")

    # FEATURE: News Feed (MarketAux)
    st.sidebar.markdown("### 📰 NEWS")
    for n in fetch_news(TICKER):
        st.sidebar.markdown(f"<a href='{n['url']}' style='color:#00FF41;font-size:12px;'>{n['title'][:45]}...</a>", unsafe_allow_html=True)

    # FEATURE: AI Projection (Degree 2 Polynomial)
    y = df['close'].values.astype(float)
    x = np.arange(len(y))
    poly = np.poly1d(np.polyfit(x, y, 2)) # Upgraded to curved prediction
    f_steps = 15
    y_proj = poly(np.arange(len(x), len(x) + f_steps))
    
    st.title(f"{info.get('name', TICKER)}")
    st.markdown(f"Target: <span class='proj-glow'>${y_proj[-1]:.2f}</span>", unsafe_allow_html=True)

    # FEATURE: Metric Grid
    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"${y[-1]:.2f}")
    m2.metric("52W High", f"${info.get('fifty_two_week_high', 'N/A')}")
    m3.metric("Trend", "BULLISH" if y_proj[-1] > y[-1] else "BEARISH")

    # FEATURE: Dynamic Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['close'], name="Actual", line=dict(color="#00FF41", width=3)))
    
    f_dates = [df.index[-1] + (df.index[-1] - df.index[-2]) * i for i in range(1, f_steps + 1)]
    fig.add_trace(go.Scatter(x=f_dates, y=y_proj, name="AI Path", line=dict(color="#00FF41", width=2, dash='dot')))
    
    fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0), height=400)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Connection Error. Check API keys.")