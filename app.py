import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np

# --- 1. APP CONFIG ---
# 'auto' allows the sidebar to collapse into a thin strip on mobile
st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="auto")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. RESTORED FULL WARNING ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: The data and 'predictions' shown here are for educational purposes only. This AI does not provide financial advice. Trading involves significant risk of loss. Always consult a certified professional before making investment decisions.")

# --- 3. UI STYLING ---
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

    /* Mobile-specific: Shrink star & keep 2x2 grid */
    @media (max-width: 640px) {
        div[data-testid="column"] { width: 100% !important; flex: 1 1 calc(50% - 10px) !important; }
        
        /* Smaller star button on mobile */
        div[data-testid="stVerticalBlock"] > div:nth-child(2) button {
            font-size: 12px !important;
            padding: 2px !important;
            min-height: 25px !important;
        }
    }

    /* Input styling */
    div[data-testid="stTextInput"] > div > div > input {
        border: 1px solid #00FF41 !important;
        background-color: #161b22 !important;
        color: #00FF41 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. UTILITIES ---
def format_val(num):
    if num is None or isinstance(num, pd.Series): return "N/A"
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B', 'T']:
            if abs(num) < 1000.0: return f"{num:3.1f}{unit}"
            num /= 1000.0
        return f"{num:.1f}P"
    except: return "N/A"

@st.cache_data(ttl=60)
def get_watchlist_info(tickers):
    results = []
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period="2d")
            if len(h) >= 2:
                change = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
                results.append({"t": t, "c": change})
        except: continue
    return results

# --- 5. SIDEBAR ---
st.sidebar.title("💠 SENTINEL")
TICKER = st.sidebar.text_input("SEARCH", st.session_state.get('current_ticker', 'NVDA')).upper()
st.session_state.current_ticker = TICKER

# Timeframe order preserved with YTD last
time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "1Y": "1y", "5Y": "5y", "YTD": "ytd"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=3)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 WATCHLIST")
if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]

for item in get_watchlist_info(st.session_state.favorites):
    col_b, col_t = st.sidebar.columns([3, 2])
    if col_b.button(f" {item['t']}", key=f"fav_{item['t']}", use_container_width=True):
        st.session_state.current_ticker = item['t']
        st.rerun()
    color = "#00FF41" if item['c'] >= 0 else "#FF3131"
    col_t.markdown(f"<p style='color:{color}; font-weight:bold; margin-top:5px; text-align:right;'>{item['c']:+.2f}%</p>", unsafe_allow_html=True)

# --- 6. MAIN CONTENT ---
try:
    asset = yf.Ticker(TICKER)
    df = asset.history(period=time_map[selected_label], interval="1m" if selected_label=="1D" else "1d")
    
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        info = asset.info
        curr_p = df['Close'].iloc[-1]
        diff = curr_p - df['Close'].iloc[0]
        
        # Header Row
        c_head, c_star = st.columns([0.92, 0.08])
        c_head.title(f"{info.get('longName', TICKER)}")
        
        # Mini Star Toggle
        is_fav = TICKER in st.session_state.favorites
        if c_star.button("★" if is_fav else "☆", use_container_width=True):
            if is_fav: st.session_state.favorites.remove(TICKER)
            else: st.session_state.favorites.append(TICKER)
            st.rerun()

        # AI Projection with Help Tooltip
        y_vals = df['Close'].values
        slope, intercept = np.polyfit(np.arange(len(y_vals)), y_vals, 1)
        pred = slope * (len(y_vals)) + intercept
        st.markdown(f"### 🔮 AI PROJECTION: <span style='color:#00FF41;'>${pred:.2f}</span>", 
                    help="Calculated using linear regression on the current chart trend. This is a mathematical estimate, not a market guarantee.", 
                    unsafe_allow_html=True)

        # 2x2 Metrics with Hover Explanations
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        
        m1.metric("Market Price", f"${curr_p:.2f}", help="The last known trading price of the asset.")
        m2.metric("Trend Velocity", f"{slope:+.4f}", help="The rate of price change. Higher values indicate a stronger upward momentum.")
        m3.metric("Market Cap", format_val(info.get('marketCap')), help="The total dollar market value of a company's outstanding shares of stock.")
        m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}", help="Price-to-Earnings Ratio. It measures current share price relative to per-share earnings.")

        # Graph Settings: Pan Mode & Lighter Fill
        l_col = "#00FF41" if diff >= 0 else "#FF3131"
        f_col = "rgba(0, 255, 65, 0.12)" if diff >= 0 else "rgba(255, 49, 49, 0.12)"
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], fill='tozeroy', 
                                 line=dict(color=l_col, width=3), fillcolor=f_col, name="Price"))
        
        # Prediction line
        pred_idx = df.index[-1] + (df.index[-1] - df.index[-2])
        fig.add_trace(go.Scatter(x=[df.index[-1], pred_idx], y=[curr_p, pred], 
                                 line=dict(color='white', width=2, dash='dot'), name="Forecast"))

        fig.update_layout(template="plotly_dark", height=400, dragmode='pan', margin=dict(l=0, r=0, t=10, b=0),
                          xaxis=dict(showgrid=False), yaxis=dict(side="right", gridcolor="rgba(255,255,255,0.05)"))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # News Section
        st.subheader("📰 Headlines")
        news_list = asset.news
        if news_list:
            for n in news_list[:4]:
                title = n.get('title') or "Stock Update"
                url = n.get('link') or n.get('url')
                with st.expander(title):
                    if url: st.markdown(f"**[View Article]({url})**")

        # Sidebar Export
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 DOWNLOAD CSV", df.to_csv().encode('utf-8'), f"{TICKER}.csv", use_container_width=True)

except Exception:
    st.info("Sentinel operational. Search for a ticker to begin.")