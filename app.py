import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. RESTORED FULL WARNING ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: The data and 'predictions' shown here are for educational purposes only. This AI does not provide financial advice. Trading involves significant risk of loss. Always consult a certified professional before making investment decisions.")

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

# --- 5. SIDEBAR ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "1Y": "1y", "5Y": "5y", "YTD": "ytd"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=3)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 WATCHLIST")
if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]

for fav in st.session_state.favorites:
    if st.sidebar.button(f" {fav}", key=f"side_{fav}", use_container_width=True):
        st.session_state.current_ticker = fav
        st.rerun()

# --- 6. MAIN CONTENT ---
try:
    # Stable fetch with MultiIndex fix
    df = yf.download(TICKER, period=time_map[selected_label], 
                     interval="1m" if selected_label=="1D" else "1d", progress=False)
    
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        asset = yf.Ticker(TICKER)
        info = asset.info
        curr_p = float(df['Close'].iloc[-1])
        diff = curr_p - float(df['Close'].iloc[0])
        
        # Header
        c_title, c_star = st.columns([0.9, 0.1])
        c_title.title(f"{info.get('longName', TICKER)}")
        
        if c_star.button("★" if TICKER in st.session_state.favorites else "☆"):
            if TICKER in st.session_state.favorites: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # AI Projection
        y_vals = df['Close'].values.flatten()
        slope, _ = np.polyfit(np.arange(len(y_vals)), y_vals, 1)
        pred = slope * (len(y_vals)) + df['Close'].iloc[0]
        st.markdown(f"### 🔮 AI PROJECTION: <span style='color:#00FF41;'>${pred:.2f}</span>", unsafe_allow_html=True)

        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Price", f"${curr_p:.2f}")
        m2.metric("Velocity", f"{slope:+.3f}")
        m3.metric("Market Cap", format_val(info.get('marketCap')))
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")

        # Graph: Pan Default + Lighter Fill
        l_col = "#00FF41" if diff >= 0 else "#FF3131"
        f_col = "rgba(0, 255, 65, 0.1)" if diff >= 0 else "rgba(255, 49, 49, 0.1)"
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', 
                                 line=dict(color=l_col, width=3), fillcolor=f_col))
        
        fig.update_layout(template="plotly_dark", height=450, dragmode='pan', margin=dict(l=0, r=0, t=0, b=0),
                          xaxis=dict(showgrid=False), yaxis=dict(side="right", gridcolor="rgba(255,255,255,0.05)"))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # News
        st.subheader("📰 News Headlines")
        for n in asset.news[:4]:
            with st.expander(n.get('title', 'News Update')):
                st.markdown(f"[Read Article]({n.get('link')})")

except Exception:
    st.info("Sentinel operational. Search for a ticker to begin.")