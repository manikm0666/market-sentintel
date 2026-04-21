import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
import time

# --- 1. APP CONFIG ---
st.set_page_config(page_title="AI Market Sentinel", layout="wide")
st_autorefresh(interval=60 * 1000, key="sentinel_refresh")

# --- 2. LEGAL WARNING ---
st.warning("⚠️ **FINANCIAL DISCLAIMER**: The data and 'predictions' shown here are for educational purposes only. This AI does not provide financial advice. Trading involves significant risk of loss. Always consult a certified professional before making investment decisions.")

# Initialize Session States
if 'favorites' not in st.session_state:
    st.session_state.favorites = ["AAPL", "MSFT", "NVDA", "^GSPC"]
if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = "NVDA"

# --- 3. UI STYLING ---
st.markdown("""
    <style>
    div[data-testid="stTextInput"] > div > div > input { border: 2px solid #00FF41 !important; background-color: #161b22 !important; color: #00FF41 !important; }
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stMetric { background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(128,128,128,0.1); }
    [data-testid="stSidebar"] { background-color: #0E1117; border-right: 1px solid rgba(128,128,128,0.2); }
    button[title="Change Theme"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. UTILITIES ---
def format_large_number(num):
    if num is None or isinstance(num, pd.Series): return "N/A"
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B', 'T']:
            if abs(num) < 1000.0: return f"{num:3.2f}{unit}"
            num /= 1000.0
        return f"{num:.2f}P"
    except: return "N/A"

@st.cache_data(ttl=60)
def get_sidebar_data(tickers):
    results = []
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period="2d")
            if len(h) >= 2:
                curr, prev = float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
                results.append({"t": t, "p": curr, "c": ((curr - prev) / prev) * 100})
        except: continue
    return results

# --- 5. SIDEBAR ---
st.sidebar.markdown("### 💠 TERMINAL CONTROLS")
TICKER = st.sidebar.text_input("ASSET SEARCH", st.session_state.current_ticker).upper()
st.session_state.current_ticker = TICKER

st.sidebar.markdown("---")
time_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "YTD": "ytd", "1Y": "1y"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()), index=3)

# --- THE RETURN OF EXPORT ---
st.sidebar.markdown("### 📥 DATA EXTRACTION")
# This will be populated once the data is fetched below

st.sidebar.markdown("---")
st.sidebar.markdown("### 📂 WATCHLIST")
watchlist = get_sidebar_data(st.session_state.favorites)
for item in watchlist:
    col_btn, col_txt = st.sidebar.columns([3, 2])
    if col_btn.button(f" {item['t']}", key=f"fav_{item['t']}", use_container_width=True):
        st.session_state.current_ticker = item['t']
        st.rerun()
    color = "#00FF41" if item['c'] >= 0 else "#FF3131"
    col_txt.markdown(f"<p style='color:{color}; font-weight:bold; text-align:right; margin-top:5px;'>{item['c']:+.2f}%</p>", unsafe_allow_html=True)

# --- 6. MAIN DASHBOARD ---
try:
    if TICKER:
        asset = yf.Ticker(TICKER)
        df = asset.history(period=time_map[selected_label], interval="1m" if selected_label=="1D" else "1d")
        
        if not df.empty:
            info = asset.info
            curr_p, start_p = float(df['Close'].iloc[-1]), float(df['Close'].iloc[0])
            diff = curr_p - start_p
            
            # Export Logic (Populating the sidebar button)
            csv_data = df.to_csv().encode('utf-8')
            st.sidebar.download_button(
                label=f"EXPORT {TICKER} CSV",
                data=csv_data,
                file_name=f"sentinel_{TICKER}_{selected_label}.csv",
                mime="text/csv",
                use_container_width=True
            )

            # TITLE & STAR
            t_col, s_col = st.columns([9, 1])
            t_col.header(f"{info.get('longName', TICKER)} ({TICKER})")
            is_fav = TICKER in st.session_state.favorites
            if s_col.button("★" if is_fav else "☆"):
                if is_fav: st.session_state.favorites.remove(TICKER)
                else: st.session_state.favorites.append(TICKER)
                st.rerun()

            # 🔮 AI PROJECTION
            y = df['Close'].values
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            prediction = slope * (len(y)) + intercept
            
            st.markdown(f"### 🔮 AI PROJECTION: <span style='color:#00FF41;'>${prediction:.2f}</span>", unsafe_allow_html=True)
            
            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Market Price", f"${curr_p:.2f}")
            m2.metric("Trend Velocity", f"{slope:+.4f}")
            m3.metric("Market Cap", format_large_number(info.get('marketCap')))
            m4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")

            # GRAPH
            is_bullish = diff >= 0
            line_color = "#00FF41" if is_bullish else "#FF3131"
            bg_color = "rgba(0, 255, 65, 0.15)" if is_bullish else "rgba(255, 49, 49, 0.15)"
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index, y=df['Close'], 
                fill='tozeroy', 
                line=dict(color=line_color, width=3),
                fillcolor=bg_color,
                name="Actual"
            ))
            
            pred_index = df.index[-1] + (df.index[-1] - df.index[-2])
            fig.add_trace(go.Scatter(
                x=[df.index[-1], pred_index], 
                y=[curr_p, prediction], 
                line=dict(color='white', width=2, dash='dot'), 
                name="AI Forecast"
            ))
            
            fig.update_layout(template="plotly_dark", height=450, dragmode='pan', margin=dict(l=0, r=0, t=0, b=0),
                              xaxis=dict(showgrid=False), yaxis=dict(side="right", gridcolor="rgba(255,255,255,0.05)"))
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

            # News
            st.markdown("### 📰 Recent Headlines")
            for n in asset.news[:5]:
                headline = n.get('title') or (n.get('content', {}).get('title')) or "Market Update"
                link = n.get('link') or n.get('url') or (n.get('content', {}).get('clickThroughUrl', {}).get('url'))
                with st.expander(headline):
                    if link: st.markdown(f"**[Click here to read full article]({link})**")
        else: st.error("Data unavailable.")
except Exception: st.info("Input a valid ticker.")