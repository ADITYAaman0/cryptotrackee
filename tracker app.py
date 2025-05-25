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
        if response.status_code == 200:
            return response.json()
        st.warning(f"Animation unavailable (Status {response.status_code})")
        return None
    except Exception as e:
        st.warning(f"Animation loading skipped: {str(e)}")
        return None

# Header section with fallback animation
lottie_url = "https://lottie.host/dc3d72d2-4118-4ddf-b945-0d66bc8d15e8/3jX2ZZ7UAF.json"
lottie_animation = load_lottie(lottie_url)

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
    """Initialize and return CoinGecko API client"""
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
    """Safely format float values with error handling"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

@st.cache_data(ttl=300)
def load_market_data(vs_currency: str):
    """Load and validate cryptocurrency market data"""
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency,
            per_page=50,
            order='market_cap_desc'
        )
        
        if not data:
            st.error("No data received from API")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        
        # Validate required columns
        required_columns = {
            'symbol': 'str',
            'name': 'str',
            'current_price': 'float',
            'market_cap': 'float',
            'total_volume': 'float',
            'price_change_percentage_24h': 'float',
            'image': 'str'
        }
        
        for col, dtype in required_columns.items():
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
            df[col] = df[col].astype(dtype)

        # Clean and format data
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

# Style table
def price_change_style(val):
    """Apply color coding to price changes"""
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
    """Retrieve historical price data with validation"""
    try:
        coin_data = df[df['Symbol'] == symbol].iloc[0]
        coin_id = coin_data.get('id', coin_data['name'].lower().replace(' ', '-'))
        
        data = cg.get_coin_market_chart_by_id(
            id=coin_id,
            vs_currency=vs_currency,
            days=days
        )
        
        if 'prices' not in data or not data['prices']:
            return pd.DataFrame()
            
        historical_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        historical_df['date'] = pd.to_datetime(historical_df['timestamp'], unit='ms')
        return historical_df[['date', 'price']]
    
    except Exception as e:
        st.error(f"Failed to load historical data: {str(e)}")
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
else:
    st.warning("Historical data not available for selected cryptocurrency")

# ========================
# PRICE ALERTS
# ========================
st.sidebar.header("🔔 Price Alerts")
watchlist = st.sidebar.multiselect(
    'Select coins to monitor',
    options=df['Symbol'],
    format_func=lambda x: x
)

for symbol in watchlist:
    try:
        coin_data = df[df['Symbol'] == symbol].iloc[0]
        current_price = safe_float_format(coin_data['Current Price'].split()[0])
        
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
        st.error(f"Error processing alert for {symbol}: {str(e)}")

# ========================
# NEWS SECTION
# ========================
@st.cache_data(ttl=600)
def get_crypto_news(api_key: str):
    """Fetch cryptocurrency news with error handling"""
    try:
        url = f"https://newsapi.org/v2/everything?q=cryptocurrency&apiKey={api_key}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json().get('articles', [])[:5]
    except Exception as e:
        st.error(f"News fetch failed: {str(e)}")
        return []

st.markdown("---")
st.subheader("📰 Latest Crypto News")

news_api_key = st.secrets.get("NEWSAPI_KEY")
if news_api_key:
    news_items = get_crypto_news(news_api_key)
    
    for idx, article in enumerate(news_items):
        bg_color = "#E3F2FD" if idx % 2 == 0 else "#BBDEFB"
        st.markdown(
            f"""
            <div style='
                background-color: {bg_color};
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            '>
                <h4>{article.get('title', 'No title available')}</h4>
                <p style='color: #666;'>{article.get('description', 'No description available')}</p>
                <a href="{article.get('url', '#')}" target="_blank" style='color: #2196F3;'>Read more →</a>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("Please configure NEWSAPI_KEY in Streamlit secrets to enable news features")

# ========================
# AUTO-REFRESH LOGIC
# ========================
def manage_auto_refresh(interval: int):
    """Handle automatic refresh of data"""
    current_time = time.time()
    last_refresh = st.session_state.get("last_refresh", 0)
    
    if current_time - last_refresh > interval:
        st.session_state.last_refresh = current_time
        st.experimental_rerun()

manage_auto_refresh(refresh_interval)
