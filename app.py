import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
import time

# --- 1. APP CONFIG ---
# 'auto' allows the sidebar to collapse to a thin bar on mobile
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="auto")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. RESTORED FULL WARNING ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: The data and 'predictions' shown here are for educational purposes only. This AI does not provide financial advice. Trading involves significant risk of loss. Always consult a certified professional before making investment decisions.")

# --- 3. UI STYLING (Mobile-First CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Responsive Metric Cards */
    div[data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(128,128,128,0.1);
        padding: 15px;
        border-radius: 12px;
    }

    /* Target the Toggle Star on Mobile */
    @media (max-width: 640px) {
        div[data-testid="column"] { width: 100% !important; flex: 1 1 calc(50% - 10px) !important; }
        
        /* Force smaller star button size */
        div[data-testid="column"]:nth-child(2) button {
            font-size: 14px !important;
            padding: 2px 5px !important;
            min-height: 30px !important;
            width: auto !important;
        }
    }

    /* Neon Input Borders */
    div[data-testid="stTextInput"] > div > div > input {
        border: 1px solid #00FF41 !important;
        background-color: #161b22 !important;
        color: #00FF41 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATA UTILITIES ---
def format_val(num):
    if num is None: return "N/A"
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B', 'T']:
            if abs(num) < 1000.0: return f"{num:3.1f}{unit}"
            num /= 1000.0
        return f"{num:.1f}P"
    except: return "N/A"

@st.cache_data(ttl=60)
def fetch_robust_data(ticker, period, interval):
    """Fetches data with a retry and column-flattening logic to prevent crashes."""
    for _ in range(2): # Try twice
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False, group_by='column')
            if not df.empty:
                # CRITICAL: Flatten MultiIndex columns
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df
            time.sleep(1)
        except: continue
    return pd.DataFrame()

# --- 5. SIDEBAR ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

# Order: 1D, 5D, 1M, YTD, 1Y
time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "YTD": "ytd", "1Y": "1y", "5Y": "5y"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=4)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 WATCHLIST")
if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]

# Load small snippets for watchlist
for fav in st.session_state.favorites:
    try:
        col_b, col_t = st.sidebar.columns([3, 2])
        if col_b.button(f" {fav}", key=f"btn_{fav}", use_container_width=True):
            st.session_state.current_ticker = fav
            st.rerun()
        # Fast mini-price fetch for the red/green numbers
        h = yf.Ticker(fav).fast_info['last_price']
        p = yf.Ticker(fav).fast_info['previous_close']
        c = ((h - p) / p) * 100
        color = "#00FF41" if c >= 0 else "#FF3131"
        col_t.markdown(f"<p style='color:{color}; font-weight:bold; margin-top:5px; text-align:right;'>{c:+.2f}%</p>", unsafe_allow_html=True)
    except: continue

# --- 6. MAIN CONTENT ---
df = fetch_robust_data(TICKER, time_map[selected_label], "1m" if selected_label=="1D" else "1d")

if not df.empty:
    try:
        asset = yf.Ticker(TICKER)
        info = asset.info
        curr_p = float(df['Close'].iloc[-1])
        diff = curr_p - float(df['Close'].iloc[0])
        
        # Header and Star
        c_head, c_star = st.columns([0.9, 0.1])
        c_head.title(f"{info.get('longName', TICKER)}")
        
        is_fav = TICKER in st.session_state.favorites
        if c_star.button("★" if is_fav else "☆", use_container_width=True):
            if is_fav: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # AI Projection Card
        y_vals = df['Close'].values.flatten()
        slope, intercept = np.polyfit(np.arange(len(y_vals)), y_vals, 1)
        pred = slope * (len(y_vals)) + intercept
        st.markdown(f"### 🔮 AI PROJECTION: <span style='color:#00FF41;'>${pred:.2f}</span>", 
                    help="Calculated via linear regression.", unsafe_allow_html=True)

        # 2x2 Responsive Metric Grid
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        m1.metric("Market Price", f"${curr_p:.2f}", help="Current trade price.")
        m2.metric("Trend Velocity", f"{slope:+.4f}", help="Growth rate over interval.")
        m3.metric("Market Cap", format_val(info.get('marketCap')), help="Total share value.")
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}", help="Price to earnings.")

        # Graph Settings
        l_col = "#00FF41" if diff >= 0 else "#FF3131"
        f_col = "rgba(0, 255, 65, 0.12)" if diff >= 0 else "rgba(255, 49, 49, 0.12)"
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', 
                                 line=dict(color=l_col, width=3), fillcolor=f_col, name="Price"))
        
        fig.update_layout(template="plotly_dark", height=400, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0),
                          xaxis=dict(showgrid=False), yaxis=dict(side="right", gridcolor="rgba(255,255,255,0.05)"))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # News
        st.subheader("📰 Recent Headlines")
        news_list = asset.news
        if news_list:
            for n in news_list[:4]:
                with st.expander(n.get('title', 'Market News')):
                    if n.get('link'): st.markdown(f"[Read Article]({n['link']})")

    except Exception as e:
        st.error("Error processing financial data. Try a different ticker.")
else:
    st.error(f"Error fetching data for {TICKER}. Check ticker spelling or try again.")
    st.info("Yahoo Finance may be experiencing temporary downtime.")