import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.express as px
import requests  # Corrected import
from streamlit_autorefresh import st_autorefresh

# Singleton API client
@st.experimental_singleton
def get_client():
    return CoinGeckoAPI()

cg = get_client()

# Title
st.title("🌍 Cryptocurrency Price Tracker")

# Sidebar settings
currency = st.sidebar.selectbox('Select Currency', ['usd', 'inr'], index=0)
refresh_interval = st.sidebar.slider('Refresh Interval (seconds)', 10, 300, 60)

# Auto-refresh the app
st_autorefresh(interval=refresh_interval * 1000, limit=None, key="crypto_autorefresh")

# Load data with memoization based on currency
@st.experimental_memo(ttl=refresh_interval)
def load_data(vs_currency):
    data = cg.get_coins_markets(vs_currency=vs_currency, per_page=50)
    df = pd.DataFrame(data)
    df['price_change_24h'] = df['price_change_percentage_24h']
    return df

st.subheader(f"Top 50 Cryptocurrencies (prices in {currency.upper()})")

# Fetch and display
with st.spinner('Loading data...'):
    df = load_data(currency)

st.dataframe(
    df[['name', 'current_price', 'market_cap', 'total_volume', 'price_change_24h']]
)

# Watchlist
st.sidebar.subheader('⭐ Your Watchlist')
watchlist = st.sidebar.multiselect('Select coins to watch', options=df['id'])

if watchlist:
    watch_df = df[df['id'].isin(watchlist)]
    st.subheader('🔔 Watchlist Prices')
    st.table(
        watch_df[['name', 'current_price', 'price_change_24h']]
    )

# Historical chart
coin_to_plot = st.selectbox('Select Coin for Historical Chart', options=df['id'])

def get_history(coin_id, vs_currency, days=30):
    data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
    prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms')
    return prices

history = get_history(coin_to_plot, currency)

fig = px.line(
    history, x='date', y='price',
    title=f'{coin_to_plot.upper()} - Last 30 Days',
    labels={'price': f'Price ({currency.upper()})'}
)
st.plotly_chart(fig, use_container_width=True)

# Price Alerts
st.sidebar.subheader('🔔 Set Price Alerts')
for coin in watchlist:
    coin_data = df.loc[df['id'] == coin].squeeze()
    alert_price = st.sidebar.number_input(
        f'{coin.upper()} alert (current: {coin_data.current_price:.2f})',
        min_value=0.0,
        value=float(coin_data.current_price),
        step=0.01
    )
    if coin_data.current_price >= alert_price:
        st.sidebar.warning(f'🚨 {coin.upper()} reached {coin_data.current_price:.2f} {currency.upper()}')

# News section
st.header("📰 Latest Crypto News")

@st.experimental_memo(ttl=300)
def fetch_crypto_news(api_key, page_size=5):
    url = (
        'https://newsapi.org/v2/everything'
        f'?q=cryptocurrency&language=en&pageSize={page_size}&apiKey={api_key}'
    )
    resp = requests.get(url)
    if resp.ok:
        return resp.json().get('articles', [])
    st.error("Failed to fetch news.")
    return []

news_api_key = st.secrets.get('NEWSAPI_KEY', None)
if news_api_key:
    articles = fetch_crypto_news(news_api_key)
    for art in articles:
        st.subheader(art['title'])
        st.write(art.get('description', ''))
        st.markdown(f"[Read more]({art['url']})")
else:
    st.info('Add your NEWSAPI_KEY in Streamlit secrets to enable news.')
