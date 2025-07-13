import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import ta
from streamlit_lottie import st_lottie

# APP CONFIGURATION & CSS
st.set_page_config(page_title="CRYPTO TRACKEE", page_icon="💸", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

body {
    background-color: #1e1e2f; 
    color: white;
}

.main {
    margin: 24px 0;
}

.central-header {
    font-family: 'Poppins', sans-serif;
    font-size: 3.5rem;
    text-align: center;
    color: #FFD700;
    animation: glow 1s infinite;
}

@keyframes glow {
    0% { text-shadow: 0 0 10px #FFD700, 0 0 20px #FFD700, 0 0 30px #FFD700; }
    50% { text-shadow: 0 0 20px #FF6B35, 0 0 40px #FF6B35; }
    100% { text-shadow: 0 0 10px #FFD700, 0 0 20px #FFD700, 0 0 30px #FFD700; }
}

.footer {
    text-align: center; 
    margin-top: 24px;
    font-size: 0.8rem; 
    color: #B5B5B5;
}
</style>
""", unsafe_allow_html=True)

# HEADER + LOTTIE
def load_lottie(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Failed to load animation: {e}")
        return None

with st.container():
    st.markdown("<h1 class='central-header'>CRYPTO TRACKEE</h1>", unsafe_allow_html=True)
    
    anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
    if anim: 
        st_lottie(anim, height=250, key="main_animation", speed=1.5)
    
    st.markdown("<h5 style='text-align: center; margin-top: 10px;'>Your Gateway to Cryptocurrency Market Intelligence</h5>", unsafe_allow_html=True)

# MAIN APP LOGIC
@st.cache_resource
def get_cg(): return CoinGeckoAPI()

try:
    cg = get_cg()
except Exception as e:
    st.error(f"Failed to connect to CoinGecko: {e}")
    st.stop()

# Market Data
@st.cache_data(ttl=30)
def load_market_data(currency):
    return pd.DataFrame(cg.get_coins_markets(vs_currency=currency, per_page=250, price_change_percentage='1h,24h,7d'))

# UI Components
with st.sidebar:
    currency_options = { ... }  # Keep your original currency options dictionary
    selected_currency_display = st.selectbox("💰 Select Currency", list(currency_options.keys()), index=0)
    currency = currency_options[selected_currency_display]
    st.info(f"Selected: {selected_currency_display}")
    
df = load_market_data(currency)

with st.sidebar:
    st.write("### Watchlist")
    watchlist = st.multiselect('Add to Watchlist', df['name'])

st.subheader("🔍 Search Cryptocurrency")
search_query = st.text_input("Search for a cryptocurrency", placeholder="Type to search...")

if search_query:
    filtered_data = df[df['name'].str.contains(search_query, case=False, na=False)]
else:
    filtered_data = df

st.write("Showing results for:", search_query or "All")
def hyperlink_coin_names(row):
    return f"[**{row['name']}**](#chart-{row['symbol']})"

filtered_data['name'] = filtered_data.apply(hyperlink_coin_names, axis=1)
st.write(filtered_data[['name', 'symbol', 'current_price', 'market_cap', 'price_change_percentage_24h']], unsafe_allow_html=True)

# Top Gainers and Losers
st.subheader("📈 Top 10 Gainers / 📉 Losers")
timeframe = st.selectbox("Select Timeframe", ['1h', '24h', '7d'])
gainers = df.nlargest(10, f'price_change_percentage_{timeframe}_in_currency')
losers = df.nsmallest(10, f'price_change_percentage_{timeframe}_in_currency')

st.write("### Gainers")
st.dataframe(gainers[['name', 'symbol', f'price_change_percentage_{timeframe}_in_currency']], height=200)

st.write("### Losers")
st.dataframe(losers[['name', 'symbol', f'price_change_percentage_{timeframe}_in_currency']], height=200)

# Details Section
st.subheader("📊 Cryptocurrency Details and Advanced Chart")
selected_crypto = st.selectbox("Select Cryptocurrency", df['id'].tolist())
crypto_data = df[df['id'] == selected_crypto]
if crypto_data.empty:
    st.warning("No data available for the selected cryptocurrency.")
    st.stop()
crypto_data = crypto_data.squeeze()

st.write(f"<div id='chart-{crypto_data['symbol']}'></div>", unsafe_allow_html=True)
st.write(f"**Name**: {crypto_data['name']}")
st.write(f"**Symbol**: {crypto_data['symbol'].upper()}")
currency_symbol = selected_currency_display.split('(')[1].split(')')[0]
st.write(f"**Current Price**: {currency_symbol}{crypto_data['current_price']:,.2f}")
if crypto_data['market_cap']:
    st.write(f"**Market Cap**: {currency_symbol}{crypto_data['market_cap']:,.0f}")
else:
    st.write(f"**Market Cap**: N/A")

# Chart Selection and Options
st.write("### Advanced Chart")
col1, col2 = st.columns(2)
with col1:
    time_frame_options = { ... }  # Your time frame options
    selected_timeframe = st.selectbox("📊 Time Frame", list(time_frame_options.keys()), index=2)
with col2:
    chart_type = st.selectbox("📈 Chart Type", ['Candlestick', 'Line', 'Area'], index=0)

# Technical indicators
st.write("#### Technical Indicators")
indicator_cols = st.columns(4)
with indicator_cols[0]:
    show_sma = st.checkbox("SMA (20, 50)", value=True)
with indicator_cols[1]:
    show_rsi = st.checkbox("RSI", value=True)
with indicator_cols[2]:
    show_macd = st.checkbox("MACD", value=True)
with indicator_cols[3]:
    show_bollinger = st.checkbox("Bollinger Bands", value=False)

# Get historical data
def get_coin_history(coin_id, days=30):
    try:
        data = cg.get_coin_market_chart_by_id(coin_id, vs_currency=currency, days=days)
        prices = data['prices']
        df_hist = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'], unit='ms')
        df_hist.set_index('timestamp', inplace=True)
        return df_hist
    except Exception as e:
        st.error(f"Error loading chart data: {e}")
        return pd.DataFrame()

def create_advanced_chart(df_hist, coin_name):
    if df_hist.empty:
        st.warning("No historical data available")
        return
    
    # Calculate technical indicators
    if show_sma:
        df_hist['SMA_20'] = ta.trend.sma_indicator(df_hist['price'], window=20)
        df_hist['SMA_50'] = ta.trend.sma_indicator(df_hist['price'], window=50)
    if show_rsi:
        df_hist['RSI'] = ta.momentum.rsi(df_hist['price'], window=14)
    if show_macd:
        df
