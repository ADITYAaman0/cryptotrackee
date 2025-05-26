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
    """Load Lottie animation with enhanced error handling"""
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
    /* Make the button look like plain text for a cleaner clickable row */
    div[data-testid*="stButton"] > button {
        background-color: transparent;
        color: white;
        text-align: left;
        padding: 0;
        font-weight: bold;
        font-size: 1em; /* Ensure button text matches table text size */
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
    col1, col2, col3 = st.columns([1, 3, 1])
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
    """Loads market data for top 250 coins and caches it."""
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency,
            order='market_cap_desc',
            per_page=250,  # Increased to get a wider market view for movers
            sparkline=True,
            price_change_percentage='7d'  # Explicitly request 7-day price change
        )
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_data(coin_id: str, vs_currency: str, days: int = 30):
    """Fetches historical data for a specific coin."""
    try:
        data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
        historical_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        historical_df['date'] = pd.to_datetime(historical_df['timestamp'], unit='ms')
        return historical_df[['date', 'price']]
    except Exception:
        return pd.DataFrame()


# ========================
# HELPER FOR SPARKLINE
# ========================
def create_sparkline(data):
    if not data or len(data) < 2:
        return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(data))), y=data, mode='lines',
        line=dict(color='#4CAF50' if data[-1] >= data[0] else '#F44336', width=4)
    ))
    fig.update_layout(
        showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)', width=150, height=50
    )
    try:
        buf = BytesIO()
        fig.write_image(buf, format="png", engine="kaleido")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    except Exception:
        return ""

# ========================
# SIDEBAR CONTROLS
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    supported_currencies = sorted(cg.get_supported_vs_currencies())
    default_index = supported_currencies.index('usd') if 'usd' in supported_currencies else 0
    currency = st.selectbox(
        'Select Currency', options=supported_currencies, index=default_index
    )
    refresh_interval = st.slider('Refresh Interval (seconds)', 10, 300, 60)


# ========================
# APP STATE INITIALIZATION
# ========================
if 'selected_coin_id' not in st.session_state:
    st.session_state.selected_coin_id = None

# ========================
# DATA PROCESSING
# ========================
df = load_market_data(currency)
if not df.empty:
    df['Symbol'] = df['symbol'].str.upper()
    df['Price Change (%)'] = df['price_change_percentage_24h'].fillna(0)
    # NEW: Process 7-day price change data
    df['7d % Change'] = df['price_change_percentage_7d_in_currency'].fillna(0)
    df['Logo'] = df['image']
    df['Trend Icon'] = df['Price Change (%)'].apply(lambda x: "🔺" if x > 0 else "🔻" if x < 0 else "➖")
    df['7d Sparkline'] = df['sparkline_in_7d'].apply(lambda x: create_sparkline(x.get('price', [])))

# ========================
# VIEW: COIN DETAIL PAGE
# ========================
def display_coin_details():
    """Renders the detailed view for a selected cryptocurrency."""
    selected_coin_data = df[df['id'] == st.session_state.selected_coin_id]
    
    if selected_coin_data.empty:
        st.warning("Could not find the selected coin. It may have been delisted or is unavailable. Returning to the main list.")
        st.session_state.selected_coin_id = None
        st.rerun()
        return

    coin = selected_coin_data.iloc[0]
    
    st.subheader(f"{coin['name']} ({coin['Symbol']})")
    
    if st.button("⬅️ Back to Market Overview"):
        st.session_state.selected_coin_id = None
        st.rerun()

    historical_data = get_historical_data(coin['id'], currency)
    if not historical_data.empty:
        fig = px.area(historical_data, x='date', y='price', title=f"{coin['name']} Price History (Last 30 Days)",
                      labels={'price': f'Price ({currency.upper()})', 'date': 'Date'},
                      color_discrete_sequence=['#4CAF50'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Coin Information")
    col1, col2 = st.columns(2)
    col1.metric("Current Price", f"{coin['current_price']:,.4f} {currency.upper()}", f"{coin['price_change_percentage_24h']:.2f}%")
    col2.metric("Market Cap", f"${coin['market_cap']:,}")
    col1.metric("24h Volume", f"${coin['total_volume']:,}")
    col2.metric("Market Cap Rank", f"#{coin['market_cap_rank']}")


# ========================
# NEW VIEW COMPONENT: TOP MOVERS
# ========================
def display_market_movers(movers_df, title, icon):
    """Creates a display list for top gainers or losers."""
    st.markdown(f'<p class="mover-header">{icon} {title}</p>', unsafe_allow_html=True)
    
    for _, row in movers_df.iterrows():
        change = row['7d % Change']
        color = "#4CAF50" if change >= 0 else "#F44336"
        
        st.markdown(f"""
            <div class="mover-row">
                <img src="{row['Logo']}" width="30">
                <span class="mover-name">{row['name']}</span>
                <span style="flex-grow: 1; text-align: right; color: {color}; font-weight: bold;">
                    {change:+.2f}%
                </span>
            </div>
        """, unsafe_allow_html=True)

# ========================
# VIEW: MAIN MARKET OVERVIEW
# ========================
def display_market_overview():
    """Renders the main dashboard view."""
    # --- Key Metrics ---
    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    btc_data = df[df['Symbol'] == 'BTC'].iloc[0]
    eth_data = df[df['Symbol'] == 'ETH'].iloc[0]
    top_gainer_24h = df.loc[df['Price Change (%)'].idxmax()]
    
    col1.metric(f"{btc_data['name']} ({btc_data['Symbol']})", f"{btc_data['current_price']:,} {currency.upper()}", f"{btc_data['Price Change (%)']:.2f}%")
    col2.metric(f"{eth_data['name']} ({eth_data['Symbol']})", f"{eth_data['current_price']:,} {currency.upper()}", f"{eth_data['Price Change (%)']:.2f}%")
    col3.metric(f"Top 24h Gainer: {top_gainer_24h['name']}", f"{top_gainer_24h['current_price']:,} {currency.upper()}", f"{top_gainer_24h['Price Change (%)']:.2f}%")
    st.markdown("---")

    # --- NEW: Weekly Top Movers Section ---
    st.subheader("Weekly Market Movers")
    top_gainers = df.sort_values(by='7d % Change', ascending=False).head(10)
    top_losers = df.sort_values(by='7d % Change', ascending=True).head(10)
    
    gainer_col, loser_col = st.columns(2)
    with gainer_col:
        display_market_movers(top_gainers, "Top Gainers (7d)", "🚀")
    with loser_col:
        display_market_movers(top_losers, "Top Losers (7d)", "📉")
    st.markdown("---")


    # --- Main Market Table ---
    st.subheader("Market Overview")
    display_df = df.head(50) # Display only top 50 by market cap in the main table
    
    header_cols = st.columns([0.5, 2, 1, 2, 1.5, 2.5])
    header_cols[0].write("**#**")
    header_cols[1].write("**Coin**")
    header_cols[2].write("**Price**")
    header_cols[3].write("**24h %**")
    header_cols[4].write("**Market Cap**")
    header_cols[5].write("**7d Sparkline**")

    for _, row in display_df.iterrows():
        cols = st.columns([0.5, 2, 1, 2, 1.5, 2.5])
        cols[0].write(f"**{row['market_cap_rank']}**")
        
        if cols[1].button(f"{row['name']} ({row['Symbol']})", key=f"coin_{row['id']}"):
            st.session_state.selected_coin_id = row['id']
            st.rerun()
            
        cols[2].write(f"{row['current_price']:,.4f}")
        
        price_change_color = "#4CAF50" if row['Price Change (%)'] >= 0 else "#F44336"
        cols[3].markdown(f'<b style="color: {price_change_color};">{row["Price Change (%)"]:+.2f}%</b>', unsafe_allow_html=True)
        
        cols[4].write(f"${row['market_cap']:,}")
        if row['7d Sparkline']:
            cols[5].markdown(f"<img src='{row['7d Sparkline']}'>", unsafe_allow_html=True)


# ========================
# MAIN APP LOGIC (CONTROLLER)
# ========================
if df.empty:
    st.warning("Could not load market data. Please check your connection or try again later.")
else:
    if st.session_state.selected_coin_id:
        display_coin_details()
    else:
        display_market_overview()

# ========================
# SIDEBAR: PRICE ALERTS
# ========================
with st.sidebar:
    st.header("🔔 Price Alerts")
    if not df.empty:
        watchlist = st.multiselect('Select coins to monitor', options=df['name'].unique())
        for coin_name in watchlist:
            coin_data = df[df['name'] == coin_name].iloc[0]
            current_price = coin_data['current_price']
            alert_price = st.number_input(f"Alert for {coin_name}", value=float(current_price * 1.05), key=f"alert_{coin_name}")
            if current_price >= alert_price > 0:
                st.success(f"🚨 {coin_name} has reached your target of {alert_price:,.2f}!")
                st.balloons()
    else:
        st.info("Data not available for setting alerts.")

# ========================
# AUTO-REFRESH LOGIC
# ========================
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()
