import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.express as px
import requests
import time
from streamlit_lottie import st_lottie
import plotly.graph_objects as go
import base64
from io import BytesIO

# ========================
# APP CONFIGURATION
# ========================
st.set_page_config(
    page_title="Crypto Tracker Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# CUSTOM STYLING (CSS) & LOTTIE ANIMATION
# ========================
def load_lottie(url: str):
    """Load Lottie animation with enhanced error handling"""
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Custom CSS for modern card-like layout and styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #FFFFFF;
        margin-bottom: 20px;
    }
    .stMetric {
        background-color: #262730;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #4CAF50;
    }
    .stMetric > label {
        color: #8A8D93; /* Metric label color */
    }
    .stMetric > div > div > p {
        color: #FAFAFA; /* Metric value color */
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    thead > tr > th {
        background-color: #4CAF50 !important;
        color: white !important;
        font-weight: bold;
    }
    tbody > tr:hover {
        background-color: #3C3D42 !important;
    }
    </style>
""", unsafe_allow_html=True)


with st.container():
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        lottie_animation = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if lottie_animation:
            st_lottie(lottie_animation, height=200, key="header_anim")
        st.markdown("<p class='main-header'>Crypto Tracker Dashboard</p>", unsafe_allow_html=True)
    st.markdown("---")


# ========================
# CORE FUNCTIONALITY
# ========================
@st.cache_resource
def get_coingecko_client():
    return CoinGeckoAPI()

cg = get_coingecko_client()

@st.cache_data(ttl=86400)
def get_all_supported_currencies():
    """Fetches all supported vs_currencies from CoinGecko API."""
    try:
        currencies = cg.get_supported_vs_currencies()
        return sorted(currencies)
    except Exception:
        return sorted(['usd', 'eur', 'jpy', 'gbp', 'btc', 'eth'])

# ========================
# HELPER FOR SPARKLINE
# ========================
def create_sparkline(data):
    """Creates a base64 encoded sparkline image from a list of prices."""
    if not data or len(data) < 2:
        return ""
    
    fig = go.Figure(go.Scatter(
        x=list(range(len(data))),
        y=data,
        mode='lines',
        line=dict(color='#4CAF50' if data[-1] >= data[0] else '#F44336', width=4)
    ))
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        width=150,
        height=50
    )
    
    # Save image to a bytes buffer
    buf = BytesIO()
    fig.write_image(buf, format="png")
    # Encode buffer to base64
    img_str = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# ========================
# SIDEBAR CONTROLS
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    
    supported_currencies = get_all_supported_currencies()
    default_index = supported_currencies.index('usd') if 'usd' in supported_currencies else 0
    currency = st.selectbox(
        'Select Currency',
        options=supported_currencies,
        index=default_index,
        help="Select the currency for displaying prices."
    )
    refresh_interval = st.slider('Refresh Interval (seconds)', 10, 300, 60, help="Set how often the data should refresh.")

# ========================
# DATA LOADING & PROCESSING
# ========================
@st.cache_data(ttl=60)
def load_market_data(vs_currency: str):
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency,
            per_page=50,
            order='market_cap_desc',
            sparkline=True  # Request sparkline data
        )
        df = pd.DataFrame(data)
        
        # Data processing and feature engineering
        df['Symbol'] = df['symbol'].str.upper()
        df['Price Change (%)'] = df['price_change_percentage_24h'].fillna(0)
        df['Logo'] = df['image'].apply(lambda x: f"<img src='{x}' width='30'>")
        df['Trend Icon'] = df['Price Change (%)'].apply(lambda x: "🔺" if x > 0 else "🔻" if x < 0 else "➖")
        df['7d Sparkline'] = df['sparkline_in_7d'].apply(lambda x: create_sparkline(x.get('price', [])))

        return df
    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        return pd.DataFrame()

df = load_market_data(currency)

# ========================
# MAIN DISPLAY: KPI METRICS
# ========================
if not df.empty:
    st.subheader("📊 Key Metrics")
    btc_data = df[df['Symbol'] == 'BTC'].iloc[0]
    eth_data = df[df['Symbol'] == 'ETH'].iloc[0]
    top_gainer = df.loc[df['Price Change (%)'].idxmax()]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label=f"{btc_data['name']} ({btc_data['Symbol']})",
            value=f"{btc_data['current_price']:,} {currency.upper()}",
            delta=f"{btc_data['Price Change (%)']:.2f}%"
        )
    with col2:
        st.metric(
            label=f"{eth_data['name']} ({eth_data['Symbol']})",
            value=f"{eth_data['current_price']:,} {currency.upper()}",
            delta=f"{eth_data['Price Change (%)']:.2f}%"
        )
    with col3:
        st.metric(
            label=f"Top Gainer: {top_gainer['name']} ({top_gainer['Symbol']})",
            value=f"{top_gainer['current_price']:,} {currency.upper()}",
            delta=f"{top_gainer['Price Change (%)']:.2f}%"
        )
    st.markdown("---")

# ========================
# MAIN DISPLAY: DATA TABLE
# ========================
if not df.empty:
    st.subheader("Market Overview")
    
    # Prepare dataframe for display
    display_df = df[[
        'Logo', 'name', 'Symbol', 'current_price', 'Price Change (%)', 'Trend Icon', 'market_cap', 'total_volume', '7d Sparkline'
    ]].rename(columns={
        'name': 'Name',
        'current_price': 'Current Price',
        'market_cap': 'Market Cap',
        'total_volume': '24h Volume'
    })

    # Render dataframe as HTML to allow custom images/styles
    st.markdown(
        display_df.to_html(
            escape=False,
            formatters={
                'Current Price': lambda x: f"<b>{x:,.4f} {currency.upper()}</b>",
                'Price Change (%)': lambda x: f'<b style="color: {"#4CAF50" if x >= 0 else "#F44336"};">{x:+.2f}%</b>',
                'Market Cap': lambda x: f"${x:,.0f}",
                '24h Volume': lambda x: f"${x:,.0f}",
                '7d Sparkline': lambda x: f"<img src='{x}'>",
            },
            index=False
        ),
        unsafe_allow_html=True
    )
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)


# ========================
# HISTORICAL PRICE CHART
# ========================
if not df.empty:
    st.markdown("---")
    st.subheader("📈 Historical Price Chart")
    selected_coin = st.selectbox('Select Cryptocurrency', options=df['name'].unique(), index=0)

    @st.cache_data(ttl=3600)
    def get_historical_data(coin_id: str, vs_currency: str, days: int = 30):
        try:
            data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
            historical_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            historical_df['date'] = pd.to_datetime(historical_df['timestamp'], unit='ms')
            return historical_df[['date', 'price']]
        except Exception:
            return pd.DataFrame()

    coin_id = df[df['name'] == selected_coin].iloc[0]['id']
    historical_data = get_historical_data(coin_id, currency)
    if not historical_data.empty:
        fig = px.area(
            historical_data, x='date', y='price', title=f"{selected_coin} Price History",
            labels={'price': f'Price ({currency.upper()})', 'date': 'Date'},
            color_discrete_sequence=['#4CAF50']
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

# ========================
# PRICE ALERTS (WITH ANIMATION)
# ========================
with st.sidebar:
    st.header("🔔 Price Alerts")
    watchlist = st.multiselect('Select coins to monitor', options=df['name'].unique())

    for coin_name in watchlist:
        coin_data = df[df['name'] == coin_name].iloc[0]
        current_price = coin_data['current_price']
        
        alert_price = st.number_input(
            f"Alert for {coin_name} ({currency.upper()})",
            min_value=0.0, value=float(current_price * 1.05), step=0.01,
            key=f"alert_{coin_name}",
            help=f"Set a price target. Current price: {current_price:,.4f}"
        )
        
        if current_price >= alert_price and alert_price > 0:
            st.success(f"🚨 {coin_name} reached your target of {alert_price:,.2f}!")
            st.balloons() # ANIMATION TRIGGER

# ========================
# AUTO-REFRESH LOGIC
# ========================
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0

if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()
