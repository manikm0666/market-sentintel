import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import numpy as np
from datetime import datetime, timedelta
from twelvedata import TDClient

# --- 1. CONFIGURATION ---
# Get your free key at twelvedata.com
API_KEY = "79c371cc5cf04adb94d7038c449d2c01" 

st.set_page_config(page_title="Market Sentinel Pro", layout="wide")

# --- 2. THE ENGINE ---
@st.cache_data(ttl=60)
def fetch_market_data(ticker, interval):
    """Fetches high-quality financial data without scraping risks."""
    try:
        td = TDClient(apikey=API_KEY)
        
        # Twelve Data separates time series from summary quotes
        ts = td.time_series(
            symbol=ticker,
            interval=interval,
            outputsize=100,
            order="ASC"
        ).as_pandas()

        quote = td.quote(symbol=ticker).as_json()
        
        return ts, quote
    except Exception as e:
        st.error(f"📡 API Connection Lost: {e}")
        return None, None

# --- 3. UI CONTROLS ---
st_autorefresh(interval=60 * 1000, key="data_refresh")

TICKER = st.sidebar.text_input("SYMBOL", value="NVDA").upper()
# Map Streamlit labels to Twelve Data intervals
time_map = {"1D": "1min", "1W": "15min", "1M": "1h", "1Y": "1day"}
selected_label = st.sidebar.selectbox("TIMEFRAME", list(time_map.keys()))

# --- 4. MAIN DASHBOARD ---
df, info = fetch_market_data(TICKER, time_map[selected_label])

if df is not None and not df.empty:
    # Ensure column names match Twelve Data's format (lowercase)
    y = df['close'].values.astype(float)
    x = np.arange(len(y))
    
    # AI Projection (Linear Regression)
    slope, intercept = np.polyfit(x, y, 1)
    f_steps = max(int(len(x) * 0.15), 5)
    y_proj = slope * (np.arange(len(x), len(x) + f_steps)) + intercept
    
    st.markdown(f"### 🔮 PROJECTED TARGET: **${y_proj[-1]:.2f}**")

    # Metrics Grid using real-time Quote API
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Price", f"${y[-1]:.2f}")
    m2.metric("Velocity", f"{slope:+.4f}")
    m3.metric("52W High", f"${info.get('fifty_two_week_high', 'N/A')}")
    m4.metric("Avg Vol", info.get('average_volume', 'N/A'))

    # Plotly Visuals
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['close'], name="Market", line=dict(color="#00FF41")))
    
    # Projection Path
    f_dates = [df.index[-1] + (df.index[-1] - df.index[-2]) * i for i in range(1, f_steps + 1)]
    fig.add_trace(go.Scatter(x=f_dates, y=y_proj, name="AI Path", line=dict(dash='dot')))
    
    fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("🔄 Connecting to Market Data Stream...")