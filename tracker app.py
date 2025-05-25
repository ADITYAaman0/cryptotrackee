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

# Load Lottie animation JSON from URL with enhanced error handling
def load_lottie(url: str):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        st.error(f"Failed to load animation: HTTP {r.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error loading animation: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error loading animation: {str(e)}")
        return None

# Lottie animation in header with fallback
lottie_crypto = load_lottie("https://assets10.lottiefiles.com/packages/lf20_jhxuit3m.json")

# Header section with error resilience
header_container = st.container()
with header_container:
    if lottie_crypto:
        try:
            st_lottie(lottie_crypto, height=150, key="crypto_anim")
        except Exception as e:
            st.error(f"Animation rendering failed: {str(e)}")
            st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🌍 Cryptocurrency Price Tracker</h1>", 
                        unsafe_allow_html=True)
    else:
        st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🌍 Cryptocurrency Price Tracker</h1>", 
                    unsafe_allow_html=True)

# Singleton API client using cache_resource
@st.cache_resource
def get_client():
    return CoinGeckoAPI()

cg = get_client()

# Sidebar settings
st.sidebar.header("⚙️ Settings")
currency = st.sidebar.selectbox('Select Currency', ['usd', 'inr'], index=0)
refresh_interval = st.sidebar.slider('Refresh Interval (seconds)', 10, 300, 60)

# Invoke auto-refresh
auto_refresh(refresh_interval)

# Load data with caching based on currency
@st.cache_data(ttl=refresh_interval)
def load_data(vs_currency):
    data = cg.get_coins_markets(vs_currency=vs_currency, per_page=50)
    df = pd.DataFrame(data)
    df['Price Change (%)'] = df['price_change_percentage_24h']
    df['Current Price'] = df['current_price']
    df['Symbol'] = df['symbol'].str.upper()
    df['Logo'] = df['image'].apply(lambda url: f"<img src='{url}' width='24' />")
    return df[['Logo','Symbol','name','Current Price','market_cap','total_volume','Price Change (%)']]

# Fetch and display
with st.spinner('Loading crypto data...'):
    try:
        df = load_data(currency)
    except Exception as e:
        st.error(f"Failed to load cryptocurrency data: {str(e)}")
        st.stop()

st.markdown(f"### Top 50 Cryptocurrencies (Prices in <span style='color:#2196F3;'>{currency.upper()}</span>)", 
            unsafe_allow_html=True)

# Style price-change with color
def color_positive(val): 
    return 'color: green; font-weight:bold;' if val > 0 else 'color: red; font-weight:bold;'

styled = df.style.format({
    'Current Price': '{:,.2f}',
    'market_cap': '{:,.0f}',
    'total_volume': '{:,.0f}',
    'Price Change (%)': '{:+.2f}%'
}).applymap(color_positive, subset=['Price Change (%)'])

st.table(styled)

# Watchlist
st.sidebar.header('⭐ Your Watchlist')
watchlist = st.sidebar.multiselect('Select coins to watch', options=df['Symbol'], format_func=lambda s: s)

if watchlist:
    watch_df = df[df['Symbol'].isin([s.lower() for s in watchlist])]
    st.markdown("<h3 style='color:#FF9800;'>🔔 Watchlist Prices</h3>", unsafe_allow_html=True)
    st.table(watch_df.style.applymap(color_positive, subset=['Price Change (%)']))

# Historical chart with animation on load
target = st.selectbox('Select Coin for Historical Chart', options=df['Symbol'], index=0)

@st.cache_data(ttl=refresh_interval)
def get_history(coin_symbol, vs_currency, days=30):
    try:
        row = df[df['Symbol'] == coin_symbol].iloc[0]
        coin_id = row.name if 'id' in row else row['name'].lower().replace(' ','-')
        data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
        prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms')
        return prices
    except Exception as e:
        st.error(f"Failed to load historical data: {str(e)}")
        return pd.DataFrame()

history = get_history(target, currency)
if not history.empty:
    fig = px.line(
        history, x='date', y='price',
        title=f"{target} Last 30 Days",
        labels={'price': f'Price ({currency.upper()})'},
        animation_frame=None
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No historical data available for selected coin")

# Price Alerts
st.sidebar.header('🔔 Price Alerts')
for sym in watchlist:
    try:
        row = df[df['Symbol'] == sym].iloc[0]
        current = float(row['Current Price'])
        alert_price = st.sidebar.number_input(
            f'Alert for {sym}',
            min_value=0.0,
            value=current,
            step=0.01
        )
        if current >= alert_price:
            st.balloons()
            st.markdown(f"<p style='color:red; font-size:1.2em;'>🚨 {sym} has reached {current:.2f} {currency.upper()}!</p>", 
                        unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error setting alert for {sym}: {str(e)}")

# News section with alternating card colors
st.markdown("<hr><h2 style='text-align:center; color:#9C27B0;'>📰 Latest Crypto News</h2>", 
            unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_crypto_news(api_key, page_size=5):
    try:
        url = (
            'https://newsapi.org/v2/everything'
            f'?q=cryptocurrency&language=en&pageSize={page_size}&apiKey={api_key}'
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json().get('articles', [])
    except Exception as e:
        st.error(f"News fetch failed: {str(e)}")
        return []

api_key = st.secrets.get('NEWSAPI_KEY')
if api_key:
    articles = fetch_crypto_news(api_key)
    if articles:
        for i, art in enumerate(articles):
            color = '#F3E5F5' if i%2==0 else '#E1BEE7'
            st.markdown(
                f"<div style='background-color:{color}; padding:10px; border-radius:8px;'>"
                f"<h4>{art['title']}</h4><p>{art.get('description','')}</p>"
                f"<a href='{art['url']}' target='_blank'>Read more</a></div><br>",
                unsafe_allow_html=True
            )
    else:
        st.info("No news articles found")
else:
    st.info('Add your NEWSAPI_KEY in Streamlit secrets to enable news.')
