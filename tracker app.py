import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.express as px
import requests
import time
from streamlit_lottie import st_lottie

# ========================
# APP CONFIGURATION
# ========================
st.set_page_config(
    page_title="Crypto Tracker",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# LOTTIE ANIMATION HANDLING
# ========================
def load_lottie(url: str):
    """Load Lottie animation with enhanced error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None

lottie_animation = load_lottie("https://lottie.host/dc3d72d2-4118-4ddf-b945-0d66bc8d15e8/3jX2ZZ7UAF.json")

with st.container():
    if lottie_animation:
        st_lottie(lottie_animation, height=150, key="header_anim")
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🌍 Cryptocurrency Price Tracker</h1>", 
                unsafe_allow_html=True)

# ========================
# CORE FUNCTIONALITY
# ========================
@st.cache_resource
def get_coingecko_client():
    return CoinGeckoAPI()

cg = get_coingecko_client()

# ========================
# SIDEBAR CONTROLS
# ========================
st.sidebar.header("⚙️ Settings")
currency = st.sidebar.selectbox('Select Currency', ['usd', 'eur', 'gbp', 'jpy'], index=0)
refresh_interval = st.sidebar.slider('Refresh Interval (seconds)', 10, 300, 60)

# ========================
# DATA LOADING & PROCESSING
# ========================
def safe_float_format(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

@st.cache_data(ttl=300)
def load_market_data(vs_currency: str):
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency,
            per_page=50,
            order='market_cap_desc'
        )
        
        df = pd.DataFrame(data)
        
        required_columns = [
            'symbol', 'name', 'current_price', 'market_cap',
            'total_volume', 'price_change_percentage_24h', 'image'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        df['Symbol'] = df['symbol'].str.upper()
        df['Current Price'] = df['current_price'].apply(safe_float_format)
        df['Market Cap'] = df['market_cap'].apply(safe_float_format)
        df['24h Volume'] = df['total_volume'].apply(safe_float_format)
        df['Price Change (%)'] = df['price_change_percentage_24h'].fillna(0)
        df['Logo'] = df['image'].apply(
            lambda x: f"<img src='{x}' width='24' style='image-rendering: crisp-edges;'>" if x else ""
        )

        return df[[
            'Logo', 'Symbol', 'name', 
            'Current Price', 'Market Cap',
            '24h Volume', 'Price Change (%)'
        ]]

    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        st.stop()

# ========================
# MAIN DISPLAY
# ========================
with st.spinner('Loading market data...'):
    df = load_market_data(currency)

# Format numeric columns
format_rules = {
    'Current Price': lambda x: f"{x:,.2f} {currency.upper()}",
    'Market Cap': lambda x: f"{x:,.0f} {currency.upper()}",
    '24h Volume': lambda x: f"{x:,.0f} {currency.upper()}",
    'Price Change (%)': lambda x: f"{x:+.2f}%"
}

def price_change_style(val):
    try:
        value = float(val.strip('%'))
        color = '#4CAF50' if value >= 0 else '#F44336'
        return f'color: {color}; font-weight: bold;'
    except:
        return ''

styled_df = df.style.format(format_rules)\
                   .applymap(price_change_style, subset=['Price Change (%)'])\
                   .set_properties(**{'text-align': 'left'})

st.markdown(styled_df.to_html(escape=False), unsafe_allow_html=True)
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

# ========================
# HISTORICAL PRICE CHART
# ========================
st.subheader("Historical Price Chart")
selected_coin = st.selectbox('Select Cryptocurrency', options=df['Symbol'], index=0)

@st.cache_data(ttl=3600)
def get_historical_data(symbol: str, vs_currency: str, days: int = 30):
    try:
        coin_data = df[df['Symbol'] == symbol].iloc[0]
        data = cg.get_coin_market_chart_by_id(
            id=coin_data.name,
            vs_currency=vs_currency,
            days=days
        )
        historical_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        historical_df['date'] = pd.to_datetime(historical_df['timestamp'], unit='ms')
        return historical_df[['date', 'price']]
    except Exception as e:
        st.error(f"Historical data error: {str(e)}")
        return pd.DataFrame()

historical_data = get_historical_data(selected_coin, currency)
if not historical_data.empty:
    fig = px.line(
        historical_data,
        x='date',
        y='price',
        title=f"{selected_coin} Price History ({currency.upper()})",
        labels={'price': 'Price', 'date': 'Date'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ========================
# PRICE ALERTS (FIXED)
# ========================
st.sidebar.header("🔔 Price Alerts")
watchlist = st.sidebar.multiselect(
    'Select coins to monitor',
    options=df['Symbol'].unique(),
    format_func=lambda x: x
)

for symbol in watchlist:
    try:
        coin_data = df[df['Symbol'] == symbol].iloc[0]
        current_price = coin_data['Current Price']
        
        alert_price = st.sidebar.number_input(
            f"Alert price for {symbol} ({currency.upper()})",
            min_value=0.0,
            value=current_price,
            step=0.01,
            key=f"alert_{symbol}"
        )
        
        if current_price >= alert_price:
            st.success(f"🚨 {symbol} alert triggered at {current_price:.2f} {currency.upper()}!")
            
    except Exception as e:
        st.error(f"Alert error for {symbol}: {str(e)}")

# ========================
# AUTO-REFRESH LOGIC
# ========================
def manage_auto_refresh(interval: int):
    current_time = time.time()
    last_refresh = st.session_state.get("last_refresh", 0)
    
    if current_time - last_refresh > interval:
        st.session_state.last_refresh = current_time
        st.experimental_rerun()

manage_auto_refresh(refresh_interval)
