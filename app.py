import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
from datetime import timedelta

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. LEGAL WARNING ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: The data and 'predictions' shown here are for educational purposes only. This AI does not provide financial advice.")

# --- 3. UI STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(128,128,128,0.1);
        padding: 15px;
        border-radius: 12px;
    }
    .proj-text {
        font-size: 24px;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(0,255,65,0.3);
    }
    div[data-testid="stTextInput"] > div > div > input {
        border: 1px solid #00FF41 !important;
        background-color: #161b22 !important;
        color: #00FF41 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. UTILITIES ---
def format_val(num):
    if num is None: return "N/A"
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B', 'T']:
            if abs(num) < 1000.0: return f"{num:3.1f}{unit}"
            num /= 1000.0
        return f"{num:.1f}P"
    except: return "N/A"

# --- 5. SIDEBAR ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

# Corrected Timeframe Order
time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "1Y": "1y", "5Y": "5y", "YTD": "ytd"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=3)

st.sidebar.markdown("---")
col_w, col_del = st.sidebar.columns([0.8, 0.2])
col_w.subheader("📂 WATCHLIST")
if col_del.button("🗑️"):
    st.session_state.favorites = []
    st.rerun()

if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]

for fav in st.session_state.favorites:
    if st.sidebar.button(f"★ {fav}", key=f"side_{fav}", use_container_width=True):
        st.session_state.current_ticker = fav
        st.rerun()

# --- 6. MAIN CONTENT ---
try:
    ticker_obj = yf.Ticker(TICKER)
    df = yf.download(TICKER, period=time_map[selected_label], 
                     interval="1m" if selected_label=="1D" else "1d", 
                     progress=False)
    
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Download button: Sidebar & Conditional (Only shows if fetch works)
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 DOWNLOAD CSV", df.to_csv().encode('utf-8'), f"{TICKER}.csv", use_container_width=True)
        
        info = ticker_obj.info
        curr_p = float(df['Close'].iloc[-1])
        diff = curr_p - float(df['Close'].iloc[0])
        
        # Header + Star Toggle
        c_title, c_star = st.columns([0.9, 0.1])
        c_title.title(f"{info.get('longName', TICKER)} ({TICKER})")
        
        is_fav = TICKER in st.session_state.favorites
        if c_star.button("★" if is_fav else "☆", use_container_width=True):
            if is_fav: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # AI Projection extension
        y_vals = df['Close'].values.flatten()
        x_vals = np.arange(len(y_vals))
        slope, intercept = np.polyfit(x_vals, y_vals, 1)
        
        future_steps = int(len(x_vals) * 0.15) 
        x_future = np.arange(len(x_vals), len(x_vals) + future_steps)
        y_future = slope * x_future + intercept
        
        st.markdown(f"<div class='proj-text'>🔮 AI PROJECTION: <span style='color:#00FF41;'>${y_future[-1]:.2f}</span></div>", unsafe_allow_html=True)

        # 2x2 Metric Grid
        m1, m2 = st.columns(2); m3, m4 = st.columns(2)
        m1.metric("Market Price", f"${curr_p:.2f}")
        
        # Trend Velocity Color Logic
        vel_color = "normal" if slope >= 0 else "inverse"
        m2.metric("Trend Velocity", f"{slope:+.4f}", delta=f"{slope:.4f}", delta_color=vel_color)
        
        m3.metric("Market Cap", format_val(info.get('marketCap')))
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")

        # Graph with Future Path
        l_col = "#00FF41" if diff >= 0 else "#FF3131"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', name="Price", 
                                 line=dict(color=l_col, width=3), fillcolor=f"rgba(0, 255, 65, 0.1)"))
        
        last_date = df.index[-1]
        future_dates = [last_date + timedelta(days=i) for i in range(1, future_steps + 1)]
        fig.add_trace(go.Scatter(x=future_dates, y=y_future, name="AI Projection", 
                                 line=dict(color="#00FF41", width=2, dash='dot')))
        
        fig.update_layout(template="plotly_dark", height=450, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # News Section (Bypassing blocks)
        st.subheader("📰 Recent Headlines")
        try:
            news = ticker_obj.news
            if news:
                for n in news[:5]:
                    with st.expander(n.get('title', 'Market Update')):
                        st.write(f"Source: {n.get('publisher', 'Financial News')}")
                        st.markdown(f"[Read Full Article]({n['link']})")
            else: st.info("News feed is currently limited by Yahoo Finance.")
        except: st.info("News feed is currently unavailable.")

except Exception:
    st.error(f"Error fetching {TICKER}. Please check the ticker symbol or wait 15 minutes.")