import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.express as px
import time
import request
cg = CoinGeckoAPI()

# Title
st.title("🌍 Cryptocurrency Price Tracker")

# Sidebar settings
currency = st.sidebar.selectbox('Select Currency', ['usd', 'inr'])
refresh_interval = st.sidebar.slider('Refresh Interval (seconds)', 10, 300, 60)

# Load data
@st.cache_data(ttl=refresh_interval)
def load_data():
    data = cg.get_coins_markets(vs_currency=currency, per_page=50)
    df = pd.DataFrame(data)
    return df

st.subheader(f"Top Cryptocurrencies (prices in {currency.upper()})")

df = load_data()

# Display table
st.dataframe(df[['name', 'current_price', 'market_cap', 'total_volume', 
                 'price_change_percentage_24h']])

# Watchlist
st.sidebar.subheader('⭐ Your Watchlist')
watchlist = st.sidebar.multiselect('Select coins to watch', df['id'])

if watchlist:
    watch_df = df[df['id'].isin(watchlist)]
    st.subheader('🔔 Watchlist Prices')
    st.table(watch_df[['name', 'current_price', 'price_change_percentage_24h']])

# Historical chart
coin_to_plot = st.selectbox('Select Coin for Historical Chart', df['id'])

@st.cache_data(ttl=refresh_interval)
def get_history(coin_id, days=30):
    data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=currency, days=days)
    prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms')
    return prices

history = get_history(coin_to_plot)

fig = px.line(history, x='date', y='price', title=f'{coin_to_plot.upper()} - Last 30 Days Price')
st.plotly_chart(fig)

# Price Alerts
st.sidebar.subheader('🔔 Set Price Alerts')
for coin in watchlist:
    coin_data = df[df['id'] == coin].iloc[0]
    alert_price = st.sidebar.number_input(f'Set alert for {coin} (current: {coin_data["current_price"]})', 
                                          min_value=0.0, value=float(coin_data["current_price"]))
    if coin_data['current_price'] >= alert_price:
        st.warning(f'🚨 Alert! {coin.upper()} has reached {coin_data["current_price"]} {currency.upper()}')

# News section (optional)


def fetch_crypto_news():
    api_key = 'YOUR_NEWSAPI_KEY'
    url = f'https://newsapi.org/v2/everything?q=cryptocurrency&apiKey={api_key}&language=en&pageSize=5'
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get('articles')
        return articles
    else:
        st.error("Failed to fetch news.")
        return []

st.header("📰 Latest Crypto News")

news_articles = fetch_crypto_news()

for article in news_articles:
    st.subheader(article['title'])
    st.write(article['description'])
    st.markdown(f"[Read more]({article['url']})")


# Auto-refresh
st.sidebar.write('⏳ Auto-refreshing...')
time.sleep(refresh_interval)
st.rerun()
