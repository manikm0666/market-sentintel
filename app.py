import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
import requests
from twelvedata import TDClient
from datetime import datetime

# --- CONFIGURATION ---
TD_KEY = "YOUR_TWELVE_DATA_KEY"
NEWS_KEY = "YOUR_MARKETAUX_KEY"

st.set_page_config(page_title="Sentinel Pro", layout="wide")

# Styling with conditional colors for the Prediction
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 15px; border: 1px solid #30363D; }
    .proj-label { font-size: 26px; font-weight: bold; color: #FFFFFF; }
    .val-up { color: #00FF41; text-shadow: 0 0 10px #00FF41; }
    .val-down { color: #FF3131; text-shadow: 0 0 10px #FF3131; }
    .tooltip { cursor: help; border-bottom: 1px dotted #888; font-size: 0.8em; vertical-align: super; margin-left: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINES ---
@st.cache_data(ttl=60)
def fetch_all_market(ticker, interval, outputsize=100):
    try:
        td = TDClient(apikey=TD_KEY)
        df = td.time_series(symbol=ticker, interval=interval, outputsize=outputsize, order="ASC").as_pandas()
        quote = td.quote(symbol=ticker).as_json()
        return df, quote
    except: return None, None

@st.cache_data(ttl=600)
def fetch_news(ticker):
    url = f"https://api.marketaux.com/v1/news/all?symbols={ticker}&filter_entities=true&limit=3&api_token={NEWS_KEY}"
    try: return requests.get(url).json().get('data', [])
    except: return []

# --- SIDEBAR ---
st_autorefresh(interval=60 * 1000, key="refresh")
st.sidebar.title("💠 SENTINEL PRO")
TICKER = st.sidebar.text_input("SEARCH", value=st.session_state.get('curr', 'AAPL')).upper()
st.session_state.curr = TICKER

# Added YTD Option
t_map = {"1D": "1min", "1M": "1h", "YTD": "1day", "1Y": "1day"}
sel_t = st.sidebar.selectbox("TIMEFRAME", list(t_map.keys()))

# Determine output size for YTD
output_size = 100
if sel_t == "YTD":
    days_since_jan1 = (datetime.now() - datetime(datetime.now().year, 1, 1)).days
    output_size = max(days_since_jan1, 1)

# --- MAIN DASHBOARD ---
df, info = fetch_all_market(TICKER, t_map[sel_t], outputsize=output_size)

if df is not None and not df.empty:
    # Sidebar features
    st.sidebar.download_button("📥 DOWNLOAD DATA", df.to_csv(), f"{TICKER}.csv")
    st.sidebar.markdown("### 📰 NEWS")
    for n in fetch_news(TICKER):
        st.sidebar.markdown(f"<a href='{n['url']}' style='color:#00FF41;font-size:12px;'>{n['title'][:45]}...</a>", unsafe_allow_html=True)

    # AI Prediction Logic (Degree 2 Polynomial)
    y = df['close'].values.astype(float)
    x = np.arange(len(y))
    poly = np.poly1d(np.polyfit(x, y, 2))
    
    f_steps = 15
    # Connect to the last point: we start our prediction range from the last index of 'x'
    x_future = np.arange(len(x) - 1, len(x) + f_steps)
    y_proj = poly(x_future)
    
    # UI Header & Color Logic
    is_falling = y_proj[-1] < y[-1]
    color_class = "val-down" if is_falling else "val-up"
    
    st.title(f"{info.get('name', TICKER)}")
    st.markdown(f"""
        <div class='proj-label'>
            AI Prediction: <span class='{color_class}'>${y_proj[-1]:.2f}</span>
            <span class="tooltip" title="A mathematical forecast based on recent price trends.">?</span>
        </div>
        """, unsafe_allow_html=True)

    # Metric Grid with Explanations
    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"${y[-1]:.2f}")
    m2.write("52W High <span class='tooltip' title='The highest price the stock reached in the last year.'>?</span>", unsafe_allow_html=True)
    m2.subheader(f"${info.get('fifty_two_week_high', 'N/A')}")
    
    trend_val = "BULLISH" if not is_falling else "BEARISH"
    m3.write("Trend <span class='tooltip' title='The general direction the stock is moving (Bullish = Up, Bearish = Down).'>?</span>", unsafe_allow_html=True)
    m3.subheader(trend_val)

    # Dynamic Chart
    fig = go.Figure()
    
    # Actual Data
    fig.add_trace(go.Scatter(x=df.index, y=df['close'], name="Actual", line=dict(color="#00FF41", width=3)))
    
    # Connected Future Path
    last_date = df.index[-1]
    # Simple date extension for visualization
    time_delta = (df.index[-1] - df.index[-2]) if len(df) > 1 else (df.index[-1] - df.index[-1])
    f_dates = [last_date + (time_delta * i) for i in range(0, len(x_future))]
    
    fig.add_trace(go.Scatter(x=f_dates, y=y_proj, name="AI Path", line=dict(color="#00FF41" if not is_falling else "#FF3131", width=2, dash='dot')))
    
    fig.update_layout(
        template="plotly_dark", 
        margin=dict(l=0, r=0, t=10, b=0), 
        height=450,
        dragmode='pan', # Set Pan as default
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Connection Error or Invalid Ticker. (Check API Keys)")