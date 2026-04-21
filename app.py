import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. PREMIUM UI STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(128,128,128,0.1);
        padding: 15px;
        border-radius: 12px;
    }

    /* Mobile-specific adjustments */
    @media (max-width: 640px) {
        div[data-testid="column"] { width: 100% !important; flex: 1 1 calc(50% - 10px) !important; }
        .stMetric { margin-bottom: 10px; }
    }

    /* Input styling */
    div[data-testid="stTextInput"] > div > div > input {
        border: 1px solid #00FF41 !important;
        background-color: #161b22 !important;
        color: #00FF41 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. UTILITIES ---
def format_val(num):
    if num is None or isinstance(num, pd.Series): return "N/A"
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B', 'T']:
            if abs(num) < 1000.0: return f"{num:3.1f}{unit}"
            num /= 1000.0
        return f"{num:.1f}P"
    except: return "N/A"

# --- 4. SIDEBAR ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "1Y": "1y", "5Y": "5y", "YTD": "ytd"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=3)

# --- 5. DATA FETCH ---
try:
    asset = yf.Ticker(TICKER)
    df = asset.history(period=time_map[selected_label], interval="1m" if selected_label=="1D" else "1d")
    
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        info = asset.info
        curr_p = df['Close'].iloc[-1]
        diff = curr_p - df['Close'].iloc[0]
        
        # Dashboard Header
        st.warning("⚠️ **FINANCIAL DISCLAIMER**: Educational purposes only.")
        
        col_title, col_star = st.columns([0.85, 0.15])
        col_title.title(f"{info.get('symbol', TICKER)}")
        
        if 'favorites' not in st.session_state: st.session_state.favorites = ["AAPL", "MSFT", "NVDA"]
        if col_star.button("★" if TICKER in st.session_state.favorites else "☆", use_container_width=True):
            if TICKER in st.session_state.favorites: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # AI Projection Header
        y_vals = df['Close'].values
        slope, intercept = np.polyfit(np.arange(len(y_vals)), y_vals, 1)
        pred = slope * (len(y_vals)) + intercept
        st.markdown(f"<h3 style='color:gray;'>🔮 AI PROJECTION: <span style='color:#00FF41;'>${pred:.2f}</span></h3>", unsafe_allow_html=True)

        # Responsive Metrics
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        m1.metric("Price", f"${curr_p:.2f}")
        m2.metric("Velocity", f"{slope:+.3f}")
        m3.metric("Market Cap", format_val(info.get('marketCap')))
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")

        # GRAPH: Lighter fill + Default Pan Mode
        line_color = "#00FF41" if diff >= 0 else "#FF3131"
        fill_color = "rgba(0, 255, 65, 0.1)" if diff >= 0 else "rgba(255, 49, 49, 0.1)"
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', 
                                 line=dict(color=line_color, width=3), 
                                 fillcolor=fill_color, name="Price"))
        
        # Add Prediction Forecast Line
        pred_idx = df.index[-1] + (df.index[-1] - df.index[-2])
        fig.add_trace(go.Scatter(x=[df.index[-1], pred_idx], y=[curr_p, pred], 
                                 line=dict(color='white', width=2, dash='dot'), name="Forecast"))

        fig.update_layout(
            template="plotly_dark", 
            height=400, 
            dragmode='pan',  # DEFAULT TO PAN MODE
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(side="right", gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

        # News Section
        st.subheader("📰 Recent Headlines")
        for n in asset.news[:4]:
            title = n.get('title') or "Market News"
            url = n.get('link') or n.get('url')
            with st.expander(title):
                if url: st.markdown(f"[Read Full Story]({url})")

        # Fixed Sidebar Export
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 DOWNLOAD DATA", df.to_csv().encode('utf-8'), f"{TICKER}.csv", use_container_width=True)

except Exception:
    st.info("Sentinel Active. Awaiting ticker input...")