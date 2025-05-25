import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.express as px
import requests
import time
from streamlit_lottie import st_lottie

# Page config & theming
st.set_page_config(
    page_title="Crypto Tracker",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper: Auto-refresh without external deps
def auto_refresh(interval_seconds: int):
    now = time.time()
    last = st.session_state.get("_last_refresh", None)
    if last is None:
        st.session_state._last_refresh = now
    elif now - last > interval_seconds:
        st.session_state._last_refresh = now
        st.experimental_rerun()

# Load Lottie animation with improved error handling
def load_lottie(url: str):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        st.warning(f"Animation unavailable (Status {r.status_code})")
        return None
    except Exception as e:
        st.warning(f"Animation loading skipped: {str(e)}")
        return None

# Header section with fallback
lottie_url = "https://assets2.lottiefiles.com/packages/lf20_pmvvqccx.json"  # New verified URL
lottie_crypto = load_lottie(lottie_url)

header_container = st.container()
with header_container:
    if lottie_crypto:
        st_lottie(lottie_crypto, height=150, key="crypto_anim")
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🌍 Cryptocurrency Price Tracker</h1>", 
                unsafe_allow_html=True)

# Singleton API client
@st.cache_resource
def get_client():
    return CoinGeckoAPI()

cg = get_client()

# Sidebar settings
st.sidebar.header("⚙️ Settings")
currency = st.sidebar.selectbox('Select Currency', ['usd', 'inr'], index=0)
refresh_interval = st.sidebar.slider('Refresh Interval (seconds)', 10, 300, 60)
auto_refresh(refresh_interval)

# Data loading with validation
@st.cache_data(ttl=refresh_interval)
def load_data(vs_currency):
    try:
        data = cg.get_coins_markets(vs_currency=vs_currency, per_page=50)
        df = pd.DataFrame(data)
        
        # Validate and clean data
        required_columns = ['symbol', 'name', 'current_price', 'market_cap', 
                          'total_volume', 'price_change_percentage_24h', 'image']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        df['Price Change (%)'] = df['price_change_percentage_24h'].fillna(0)
        df['Current Price'] = df['current_price'].apply(lambda x: f"{x:,.2f}")
        df['Symbol'] = df['symbol'].str.upper()
        df['Logo'] = df['image'].apply(lambda url: f"<img src='{url}' width='24'/>")
        df['market_cap'] = df['market_cap'].apply(lambda x: f"{x:,.0f}")
        df['total_volume'] = df['total_volume'].apply(lambda x: f"{x:,.0f}")

        return df[['Logo', 'Symbol', 'name', 'Current Price', 
                 'market_cap', 'total_volume', 'Price Change (%)']]
    
    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        st.stop()

# Display data
with st.spinner('Loading crypto data...'):
    df = load_data(currency)

st.markdown(f"### Top 50 Cryptocurrencies (Prices in {currency.upper()})")

# Styled table formatting
def color_positive(val):
    try:
        value = float(val.rstrip('%'))
        return 'color: green;' if value > 0 else 'color: red;'
    except:
        return ''

styled = df.style.format({
    'Price Change (%)': '{:+.2f}%'
}).applymap(color_positive, subset=['Price Change (%)'])

st.markdown(styled.to_html(escape=False), unsafe_allow_html=True)

# Rest of the code remains similar with proper error handling...
# [Include the watchlist, historical chart, price alerts, and news sections from previous versions]
