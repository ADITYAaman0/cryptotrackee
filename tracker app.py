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
    page_title="CRYPTO TRACKEE",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# CUSTOM STYLING (CSS) & LOTTIE ANIMATION
# ========================
def load_lottie(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException:
        return None

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
    div[data-testid*="stButton"] > button {
        background-color: transparent;
        color: white;
        text-align: left;
        padding: 0;
        font-weight: bold;
        font-size: 1em;
    }
    div[data-testid*="stButton"] > button:hover {
        color: #4CAF50;
        border-color: transparent;
    }
    div[data-testid*="stButton"] > button:focus {
        box-shadow: none !important;
        color: #4CAF50;
    }
    .mover-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #FFFFFF;
        padding-bottom: 10px;
        border-bottom: 2px solid #4CAF50;
    }
    .mover-row {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }
    .mover-name {
        font-weight: bold;
        margin-left: 10px;
    }
    </style>
""", unsafe_allow_html=True)

with st.container():
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        lottie_animation = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if lottie_animation:
            st_lottie(lottie_animation, height=200, key="header_anim")
        st.markdown("<p class='main-header'>Crypto Tracker Dashboard</p>", unsafe_allow_html=True)
    st.markdown("---")

# ========================
# CORE FUNCTIONALITY & DATA
# ========================
@st.cache_resource
def get_coingecko_client():
    return CoinGeckoAPI()

cg = get_coingecko_client()

@st.cache_data(ttl=60)
def load_market_data(vs_currency: str):
    """Loads market data for top 250 coins including multiple change periods."""
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency,
            order='market_cap_desc',
            per_page=250,
            sparkline=True,
            price_change_percentage='24h,7d,30d'
        )
        df = pd.DataFrame(data)
        # create separate change columns
        df['24h %'] = df['price_change_percentage_24h_in_currency'].fillna(0)
        df['7d %']  = df['price_change_percentage_7d_in_currency'].fillna(0)
        df['30d %'] = df['price_change_percentage_30d_in_currency'].fillna(0)
        # common fields
        df['Symbol'] = df['symbol'].str.upper()
        df['Logo']   = df['image']
        df['Trend Icon'] = df['price_change_percentage_24h'].apply(lambda x: '🔺' if x>0 else '🔻' if x<0 else '➖')
        df['7d Sparkline'] = df['sparkline_in_7d'].apply(lambda x: create_sparkline(x.get('price', [])))
        return df
    except Exception as e:
        st.error(f"Data loading failed: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_data(coin_id: str, vs_currency: str, days: int = 30):
    try:
        data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
        historical_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        historical_df['date'] = pd.to_datetime(historical_df['timestamp'], unit='ms')
        return historical_df[['date','price']]
    except Exception:
        return pd.DataFrame()

# sparkline helper unchanged
def create_sparkline(data):
    if not data or len(data)<2:
        return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(data))), y=data, mode='lines',
        line=dict(color='#4CAF50' if data[-1]>=data[0] else '#F44336', width=4)
    ))
    fig.update_layout(showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
                      margin=dict(l=0,r=0,t=0,b=0), plot_bgcolor='rgba(0,0,0,0)',
                      paper_bgcolor='rgba(0,0,0,0)', width=150, height=50)
    buf = BytesIO()
    fig.write_image(buf, format='png', engine='kaleido')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

# ========================
# SIDEBAR CONTROLS
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    supported = sorted(cg.get_supported_vs_currencies())
    default_idx = supported.index('usd') if 'usd' in supported else 0
    currency = st.selectbox('Select Currency', options=supported, index=default_idx)
    timeframe = st.selectbox('Select time frame for movers', options=['24h','7d','30d'], index=1)
    refresh_interval = st.slider('Refresh Interval (seconds)', 10,300,60)

# app state init
if 'selected_coin_id' not in st.session_state:
    st.session_state.selected_coin_id = None
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# load data
df = load_market_data(currency)

# helper to display movers now accepts pct_col
def display_market_movers(movers_df, title, icon, pct_col):
    st.markdown(f'<p class="mover-header">{icon} {title}</p>', unsafe_allow_html=True)
    for _, row in movers_df.iterrows():
        change = row[pct_col]
        color = '#4CAF50' if change>=0 else '#F44336'
        st.markdown(f"""
            <div class="mover-row">
                <img src="{row['Logo']}" width="30">
                <span class="mover-name">{row['name']}</span>
                <span style="flex-grow:1; text-align:right; color:{color}; font-weight:bold;">
                    {change:+.2f}%
                </span>
            </div>
        """, unsafe_allow_html=True)

# detail view (unchanged)
def display_coin_details():
    sel = df[df['id']==st.session_state.selected_coin_id]
    if sel.empty:
        st.warning("Coin not found; returning to overview.")
        st.session_state.selected_coin_id = None
        st.rerun()
    coin = sel.iloc[0]
    st.subheader(f"{coin['name']} ({coin['Symbol']})")
    if st.button("⬅️ Back to Market Overview"):
        st.session_state.selected_coin_id = None
        st.rerun()
    hist = get_historical_data(coin['id'], currency)
    if not hist.empty:
        fig = px.area(hist, x='date', y='price', title=f"{coin['name']} Price History (Last 30 Days)",
                      labels={'price':f'Price ({currency.upper()})','date':'Date'},
                      color_discrete_sequence=['#4CAF50'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Coin Information")
    c1,c2 = st.columns(2)
    c1.metric("Current Price", f"{coin['current_price']:,.4f} {currency.upper()}", f"{coin['24h %']:.2f}%")
    c2.metric("Market Cap", f"${coin['market_cap']:,}")
    c1.metric("24h Volume", f"${coin['total_volume']:,}")
    c2.metric("Market Cap Rank", f"#{coin['market_cap_rank']}")

# main overview
def display_market_overview():
    st.subheader("Key Metrics")
    c1,c2,c3 = st.columns(3)
    btc = df[df['Symbol']=='BTC'].iloc[0]
    eth = df[df['Symbol']=='ETH'].iloc[0]
    top24 = df.loc[df['24h %'].idxmax()]
    c1.metric(f"{btc['name']} ({btc['Symbol']})", f"{btc['current_price']:,} {currency.upper()}", f"{btc['24h %']:.2f}%")
    c2.metric(f"{eth['name']} ({eth['Symbol']})", f"{eth['current_price']:,} {currency.upper()}", f"{eth['24h %']:.2f}%")
    c3.metric(f"Top 24h Gainer: {top24['name']}", f"{top24['current_price']:,} {currency.upper()}", f"{top24['24h %']:.2f}%")
    st.markdown("---")

    # dynamic movers
    col_map = {'24h':'24h %','7d':'7d %','30d':'30d %'}
    pct_col = col_map[timeframe]
    st.subheader(f"Top Movers over last {timeframe}")
    gainers = df.sort_values(pct_col, ascending=False).head(10)
    losers  = df.sort_values(pct_col, ascending=True).head(10)
    g_col,l_col = st.columns(2)
    with g_col:
        display_market_movers(gainers, f"Top Gainers ({timeframe})", "🚀", pct_col)
    with l_col:
        display_market_movers(losers,  f"Top Losers ({timeframe})",  "📉", pct_col)
    st.markdown("---")

    # market table
    st.subheader("Market Overview")
    view = df.head(50)
    headers = st.columns([0.5,2,1,2,1.5,2.5])
    for h,title in enumerate(["#","Coin","Price","24h %","Market Cap","7d Sparkline"]):
        headers[h].write(f"**{title}**")
    for _,row in view.iterrows():
        cols = st.columns([0.5,2,1,2,1.5,2.5])
        cols[0].write(f"**{row['market_cap_rank']}**")
        if cols[1].button(f"{row['name']} ({row['Symbol']})", key=f"coin_{row['id']}"):
            st.session_state.selected_coin_id = row['id']
            st.rerun()
        cols[2].write(f"{row['current_price']:,.4f}")
        color = '#4CAF50' if row['24h %']>=0 else '#F44336'
        cols[3].markdown(f"<b style='color:{color};'>{row['24h %']:+.2f}%</b>", unsafe_allow_html=True)
        cols[4].write(f"${row['market_cap']:,}")
        if row['7d Sparkline']:
            cols[5].markdown(f"<img src='{row['7d Sparkline']}'>", unsafe_allow_html=True)

# CONTROLLER
if df.empty:
    st.warning("Could not load market data. Please check connection.")
else:
    if st.session_state.selected_coin_id:
        display_coin_details()
    else:
        display_market_overview()

# sidebar alerts
with st.sidebar:
    st.header("🔔 Price Alerts")
    if not df.empty:
        watchlist = st.multiselect('Select coins to monitor', options=df['name'].unique())
        for coin in watchlist:
            data = df[df['name']==coin].iloc[0]
            curr = data['current_price']
            alert = st.number_input(f"Alert for {coin}", value=float(curr*1.05), key=f"alert_{coin}")
            if curr >= alert > 0:
                st.success(f"🚨 {coin} has reached your target of {alert:,.2f}!")
                st.balloons()
    else:
        st.info("Data not available for setting alerts.")

# auto-refresh
time_diff = time.time() - st.session_state.last_refresh
if time_diff > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()
