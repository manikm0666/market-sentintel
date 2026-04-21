import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. LEGAL WARNING ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: The data and 'predictions' shown here are for educational purposes only. This AI does not provide financial advice. Trading involves significant risk of loss.")

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

# --- 5. SIDEBAR (Fixed Order & Watchlist) ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

# Corrected Order: 1D to 5Y
time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "YTD": "ytd", "1Y": "1y", "5Y": "5y"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=4)

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
    info = ticker_obj.info
    # Fetch data and flatten for chart stability
    df = yf.download(TICKER, period=time_map[selected_label], 
                     interval="1m" if selected_label=="1D" else "1d", 
                     progress=False, group_by='column')
    
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        curr_p = float(df['Close'].iloc[-1])
        diff = curr_p - float(df['Close'].iloc[0])
        
        # Display Full Name
        full_name = info.get('longName', TICKER)
        c_title, c_star = st.columns([0.9, 0.1])
        c_title.title(f"{full_name} ({TICKER})")
        
        is_fav = TICKER in st.session_state.favorites
        if c_star.button("★" if is_fav else "☆", use_container_width=True):
            if is_fav: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # AI Projection Calculation
        y_vals = df['Close'].values.flatten()
        x_vals = np.arange(len(y_vals))
        slope, intercept = np.polyfit(x_vals, y_vals, 1)
        pred = slope * (len(y_vals)) + intercept
        st.markdown(f"### 🔮 AI PROJECTION: <span style='color:#00FF41;'>${pred:.2f}</span>", help="Trend projection.", unsafe_allow_html=True)

        # 2x2 Metric Grid
        m1, m2 = st.columns(2); m3, m4 = st.columns(2)
        m1.metric("Market Price", f"${curr_p:.2f}")
        m2.metric("Trend Velocity", f"{slope:+.4f}")
        m3.metric("Market Cap", format_val(info.get('marketCap')))
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")

        # Graph with Trendline
        trend_line = slope * x_vals + intercept
        l_col = "#00FF41" if diff >= 0 else "#FF3131"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', name="Price", line=dict(color=l_col, width=3), fillcolor=f"rgba{tuple(list(int(l_col.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}"))
        fig.add_trace(go.Scatter(x=df.index, y=trend_line, name="AI Trend", line=dict(color="rgba(255,255,255,0.4)", width=2, dash='dash')))
        
        fig.update_layout(template="plotly_dark", height=450, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                          xaxis=dict(showgrid=False), yaxis=dict(side="right", gridcolor="rgba(255,255,255,0.05)"))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Download CSV restored
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 DOWNLOAD CSV", df.to_csv().encode('utf-8'), f"{TICKER}.csv", use_container_width=True)

        # Headlines Expanders fixed
        st.subheader("📰 Recent Headlines")
        news = ticker_obj.news
        if news:
            for n in news[:4]:
                with st.expander(n.get('title', 'Market Update')):
                    if n.get('link'): st.markdown(f"[Read Full Article]({n['link']})")
        else: st.info("No recent news found for this ticker.")

except Exception:
    st.error(f"Error fetching {TICKER}.")
    st.info("Yahoo Finance may be rate-limiting. Please wait 15 minutes.")