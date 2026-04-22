import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
from datetime import timedelta
import requests
import random
import time

# --- 1. GLOBAL UTILITIES (Defined first to prevent Pylance errors) ---
def format_val(num):
    """Formats large metrics into readable strings."""
    if num is None or num == "N/A": return "N/A"
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B', 'T']:
            if abs(num) < 1000.0: return f"{num:3.1f}{unit}"
            num /= 1000.0
        return f"{num:.1f}P"
    except: return "N/A"

# --- 2. ADVANCED IDENTITY ROTATION (The "Complicated" Fix) ---
def get_rotated_session():
    """Mimics different browsers to bypass Yahoo's bot detection."""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
    ]
    sess = requests.Session()
    sess.headers.update({'User-Agent': random.choice(agents)})
    # Pre-flight to get cookies
    try: sess.get("https://finance.yahoo.com", timeout=5)
    except: pass
    return sess

# --- 3. APP CONFIG ---
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

if 'session' not in st.session_state:
    st.session_state.session = get_rotated_session()

@st.cache_data(ttl=300)
def fetch_data(ticker, period, interval):
    return yf.download(ticker, period=period, interval=interval, 
                       progress=False, session=st.session_state.session)

# --- 4. UI STYLING ---
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

# --- 5. SIDEBAR ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "1Y": "1y", "5Y": "5y", "YTD": "ytd"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=3)

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Watchlist"):
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]
    st.rerun()

if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]

for fav in st.session_state.favorites:
    if st.sidebar.button(f"★ {fav}", key=f"side_{fav}", use_container_width=True):
        st.session_state.current_ticker = fav
        st.rerun()

# --- 6. MAIN ENGINE ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: Educational purposes only.")

try:
    ticker_obj = yf.Ticker(TICKER, session=st.session_state.session)
    interval = "1m" if selected_label == "1D" else "1d"
    df = fetch_data(TICKER, time_map[selected_label], interval)
    
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
        # Download Button (Conditional)
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 DOWNLOAD CSV", df.to_csv().encode('utf-8'), f"{TICKER}.csv", use_container_width=True)
        
        info = ticker_obj.info
        curr_p = float(df['Close'].iloc[-1])
        
        c_title, c_star = st.columns([0.9, 0.1])
        c_title.title(f"{info.get('longName', TICKER)} ({TICKER})")
        
        is_fav = TICKER in st.session_state.favorites
        if c_star.button("★" if is_fav else "☆", use_container_width=True):
            if is_fav: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # Projection logic
        y = df['Close'].values.flatten()
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        f_steps = int(len(x) * 0.15) 
        y_proj = slope * (np.arange(len(x), len(x) + f_steps)) + intercept
        
        st.markdown(f"<div class='proj-text'>🔮 AI PROJECTION: <span style='color:#00FF41;'>${y_proj[-1]:.2f}</span></div>", unsafe_allow_html=True)

        m1, m2 = st.columns(2); m3, m4 = st.columns(2)
        m1.metric("Current Price", f"${curr_p:.2f}")
        m2.metric("Trend Velocity", f"{slope:+.4f}", delta=f"{slope:.4f}", delta_color="normal" if slope >= 0 else "inverse")
        m3.metric("Market Cap", format_val(info.get('marketCap')))
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")

        # Plotly Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Actual", line=dict(color="#00FF41" if curr_p >= float(df['Close'].iloc[0]) else "#FF3131", width=3)))
        
        f_dates = [df.index[-1] + timedelta(days=i) for i in range(1, f_steps + 1)]
        fig.add_trace(go.Scatter(x=f_dates, y=y_proj, name="Path", line=dict(color="#00FF41", width=2, dash='dot')))
        
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

except Exception:
    # Countdown Error UI
    placeholder = st.empty()
    for seconds in range(60, 0, -1):
        placeholder.error(f"⚠️ Yahoo Limiter active for {TICKER}. Rotating identity and retrying in {seconds}s...")
        time.sleep(1)
    st.session_state.session = get_rotated_session() # Force a new identity
    st.rerun()