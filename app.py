import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np

# --- 1. APP CONFIG ---
# Reverted to 'expanded' to keep your Watchlist visible
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. FULL LEGAL WARNING ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: The data and 'predictions' shown here are for educational purposes only. This AI does not provide financial advice. Trading involves significant risk of loss. Always consult a certified professional before making investment decisions.")

# --- 3. UI STYLING (Restored Customizations) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* 2x2 Metric Cards restored */
    div[data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(128,128,128,0.1);
        padding: 15px;
        border-radius: 12px;
    }

    /* Mobile: 2x2 Grid + Small Star Fix */
    @media (max-width: 640px) {
        div[data-testid="column"] { width: 100% !important; flex: 1 1 calc(50% - 10px) !important; }
        div[data-testid="column"]:nth-child(2) button {
            font-size: 12px !important;
            padding: 2px 5px !important;
            min-height: 28px !important;
        }
    }

    /* Neon Search Input */
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

# --- 5. SIDEBAR (Full Watchlist/Favorites Restored) ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "YTD": "ytd", "1Y": "1y", "5Y": "5y"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=4)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 WATCHLIST")
if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]

# Favorites clickable list
for fav in st.session_state.favorites:
    if st.sidebar.button(f" {fav}", key=f"side_{fav}", use_container_width=True):
        st.session_state.current_ticker = fav
        st.rerun()

# --- 6. MAIN CONTENT ---
try:
    ticker_obj = yf.Ticker(TICKER)
    # Using download for stability with group_by to flatten headers
    df = yf.download(TICKER, period=time_map[selected_label], 
                     interval="1m" if selected_label=="1D" else "1d", 
                     progress=False, group_by='column')
    
    if not df.empty:
        # CLEANUP: Crucial fix for MultiIndex headers that cause blank screens
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        curr_p = float(df['Close'].iloc[-1])
        diff = curr_p - float(df['Close'].iloc[0])
        
        # Header + Favorite Star Toggle
        c_title, c_star = st.columns([0.9, 0.1])
        c_title.title(f"{TICKER} Asset Monitor")
        
        is_fav = TICKER in st.session_state.favorites
        if c_star.button("★" if is_fav else "☆", use_container_width=True):
            if is_fav: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # AI Projection with Help Tooltip
        y_vals = df['Close'].values.flatten()
        slope, _ = np.polyfit(np.arange(len(y_vals)), y_vals, 1)
        pred = slope * (len(y_vals)) + float(df['Close'].iloc[0])
        st.markdown(f"### 🔮 AI PROJECTION: <span style='color:#00FF41;'>${pred:.2f}</span>", 
                    help="Linear regression trend calculation based on current timeframe.", unsafe_allow_html=True)

        # 2x2 Metric Grid
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        
        # Fetching info safely to avoid rate-limiting crashes
        info = ticker_obj.info
        m1.metric("Market Price", f"${curr_p:.2f}", help="Last traded price.")
        m2.metric("Trend Velocity", f"{slope:+.4f}", help="Average growth per interval.")
        m3.metric("Market Cap", format_val(info.get('marketCap')), help="Total company value.")
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}", help="Price-to-Earnings.")

        # Graph Settings
        l_col = "#00FF41" if diff >= 0 else "#FF3131"
        f_col = "rgba(0, 255, 65, 0.12)" if diff >= 0 else "rgba(255, 49, 49, 0.12)"
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', 
                                 line=dict(color=l_col, width=3), fillcolor=f_col))
        
        fig.update_layout(template="plotly_dark", height=450, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0),
                          xaxis=dict(showgrid=False), yaxis=dict(side="right", gridcolor="rgba(255,255,255,0.05)"))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # News Section
        st.subheader("📰 Recent Headlines")
        for n in ticker_obj.news[:4]:
            with st.expander(n.get('title', 'Market Update')):
                if n.get('link'): st.markdown(f"**[Read Full Article]({n['link']})**")

except Exception as e:
    st.error(f"Error fetching {TICKER}. Data source may be temporarily unavailable.")
    st.info("Try refreshing or searching for a different ticker.")