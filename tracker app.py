import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.express as px
import plotly.graph_objects as go
import requests
import time
from streamlit_lottie import st_lottie
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
# CUSTOM STYLING & ANIMATION
# ========================
st.markdown("""
<style>
.central-header {
    font-size:3rem; font-weight:bold;
    text-align:center; color:#FFF;
    margin-bottom:20px;
}
/* glowing search input */
@keyframes glow {
  0%   { box-shadow: 0 0 5px #4CAF50; }
  50%  { box-shadow: 0 0 20px #4CAF50; }
  100% { box-shadow: 0 0 5px #4CAF50; }
}
[data-baseweb="input"] input {
    animation: glow 2s infinite;
    border: 2px solid #4CAF50 !important;
    border-radius: 8px;
    padding: 8px 12px !important;
}
</style>
""", unsafe_allow_html=True)

def load_lottie(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

# ========================
# INITIALIZE SESSION-STATE
# ========================
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""

# ========================
# HEADER & SEARCH BOX
# ========================
with st.container():
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim:
            st_lottie(anim, height=200)
        st.markdown("<p class='central-header'>CRYPTO TRACKEE</p>", unsafe_allow_html=True)
    st.markdown("---")

    # ——— Search + Clear Button —————————————————————————————————————————
    st.session_state.search_term = st.text_input(
        "🔍 Search Coins",
        placeholder="Type name or symbol…",
        key="search_term"
    )
    if st.button("🔙 Clear Search"):
        st.session_state.search_term = ""
        st.experimental_rerun()
    st.markdown("---")

# ========================
# DATA & HELPERS
# ========================
@st.cache_resource
def get_coingecko_client():
    return CoinGeckoAPI()

cg = get_coingecko_client()

def create_sparkline(data):
    if not data or len(data)<2:
        return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(data))), y=data, mode='lines',
        line=dict(color='#4CAF50' if data[-1]>=data[0] else '#F44336', width=2)
    ))
    fig.update_layout(
        showlegend=False, xaxis_visible=False, yaxis_visible=False,
        margin=dict(t=0,b=0,l=0,r=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        width=150, height=50
    )
    buf = BytesIO()
    fig.write_image(buf, format='png', engine='kaleido')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

@st.cache_data(ttl=60)
def load_market_data(vs_currency: str):
    data = cg.get_coins_markets(
        vs_currency=vs_currency,
        order='market_cap_desc',
        per_page=250,
        sparkline=True,
        price_change_percentage='24h,7d,30d'
    )
    df = pd.DataFrame(data)
    df['24h %'] = df['price_change_percentage_24h_in_currency'].fillna(0)
    df['7d %']  = df['price_change_percentage_7d_in_currency'].fillna(0)
    df['30d %'] = df['price_change_percentage_30d_in_currency'].fillna(0)
    df['Symbol'] = df['symbol'].str.upper()
    df['Logo']   = df['image']
    df['7d Sparkline'] = df['sparkline_in_7d'].apply(lambda x: create_sparkline(x.get('price', [])))
    return df

@st.cache_data(ttl=3600)
def get_historical_data(coin_id, vs_currency, days=30):
    chart = cg.get_coin_market_chart_by_id(coin_id, vs_currency, days)
    df = pd.DataFrame(chart['prices'], columns=['timestamp','price'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['date','price']]

@st.cache_data(ttl=3600)
def get_ohlc_data(coin_id, vs_currency, days=30):
    data = cg.get_coin_ohlc_by_id(coin_id, vs_currency, days)
    df = pd.DataFrame(data, columns=['timestamp','open','high','low','close'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['date','open','high','low','close']]

# ========================
# SIDEBAR SETTINGS
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    supported = sorted(cg.get_supported_vs_currencies())
    currency = st.selectbox('Currency', supported, index=supported.index('usd'))
    timeframe = st.selectbox('Movers Timeframe', ['24h','7d','30d'], index=1)
    refresh_interval = st.slider('Refresh Interval (s)', 10,300,60)

# ========================
# LOAD & FILTER DATA
# ========================
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

df = load_market_data(currency)

# apply search filter
if st.session_state.search_term:
    mask = (
        df['name'].str.contains(st.session_state.search_term, case=False, na=False) |
        df['Symbol'].str.contains(st.session_state.search_term, case=False, na=False)
    )
    df = df[mask]

# maintain selected_coin state
if 'selected_coin_id' not in st.session_state:
    st.session_state.selected_coin_id = None

# ========================
# DISPLAY FUNCTIONS
# ========================
def display_market_movers(df_mov, title, icon, pct_col):
    st.markdown(f"**{icon} {title}**")
    for _, r in df_mov.iterrows():
        ch, clr = r[pct_col], ('#4CAF50' if r[pct_col]>=0 else '#F44336')
        st.markdown(
            f"<div style='display:flex;align-items:center'>"
            f"<img src='{r['Logo']}' width='24'><span style='margin-left:8px'>{r['name']}</span>"
            f"<span style='margin-left:auto;color:{clr};font-weight:bold'>{ch:+.2f}%</span></div>",
            unsafe_allow_html=True
        )

def display_market_overview(df_overview):
    if df_overview.empty:
        st.warning("No coins match your search.")
        return

    st.subheader("Key Metrics")
    bcol, ecol, tcol = st.columns(3)

    # BTC
    btc_row = df_overview[df_overview['Symbol']=='BTC']
    if not btc_row.empty:
        btc = btc_row.iloc[0]
        bcol.metric("BTC", f"{btc['current_price']:.2f}", f"{btc['24h %']:.2f}%")
    else:
        bcol.metric("BTC", "N/A", "—")

    # ETH
    eth_row = df_overview[df_overview['Symbol']=='ETH']
    if not eth_row.empty:
        eth = eth_row.iloc[0]
        ecol.metric("ETH", f"{eth['current_price']:.2f}", f"{eth['24h %']:.2f}%")
    else:
        ecol.metric("ETH", "N/A", "—")

    # Top Gainer
    top = df_overview.loc[df_overview['24h %'].idxmax()]
    tcol.metric("Top 24h Gainer", f"{top['name']} ({top['24h %']:.2f}%)")
    st.markdown("---")

    # Movers
    pc = {'24h':'24h %','7d':'7d %','30d':'30d %'}[timeframe]
    gc, lc = st.columns(2)
    with gc: display_market_movers(df_overview.nlargest(10, pc), "🚀 Gainers", "🚀", pc)
    with lc: display_market_movers(df_overview.nsmallest(10, pc), "📉 Losers", "📉", pc)
    st.markdown("---")

    # Overview table
    st.subheader("Market Overview")
    tbl = df_overview.head(50)
    headers = ["#","Coin","Price","24h %","Market Cap","7d Sparkline"]
    widths  = [0.5,2,1,1,1.5,2.5]
    cols = st.columns(widths)
    for col, h in zip(cols, headers):
        col.write(f"**{h}**")
    for _, r in tbl.iterrows():
        c0, c1, c2, c3, c4, c5 = st.columns(widths)
        c0.write(r['market_cap_rank'])
        if c1.button(f"{r['name']} ({r['Symbol']})", key=r['id']):
            st.session_state.selected_coin_id = r['id']
            st.rerun()
        c2.write(f"{r['current_price']:.4f}")
        clr = '#4CAF50' if r['24h %']>=0 else '#F44336'
        c3.markdown(f"<span style='color:{clr}'>{r['24h %']:+.2f}%</span>", unsafe_allow_html=True)
        c4.write(f"${r['market_cap']:,}")
        if r['7d Sparkline']:
            c5.markdown(f"<img src='{r['7d Sparkline']}'>", unsafe_allow_html=True)

def display_coin_details():
    sel = df[df['id']==st.session_state.selected_coin_id]
    if sel.empty:
        st.warning("Coin not available. Returning…")
        st.session_state.selected_coin_id = None
        st.rerun()
    coin = sel.iloc[0]
    st.subheader(f"{coin['name']} ({coin['Symbol']})")
    if st.button("⬅️ Back"):
        st.session_state.selected_coin_id = None
        st.rerun()

    chart_type = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"])
    days = st.slider("History (days)", 7, 90, 30)

    if chart_type == "Line":
        hist = get_historical_data(coin['id'], currency, days)
        fig = px.line(hist, x='date', y='price',
                      title=f"{coin['name']} Price (Last {days}d)",
                      labels={'price':f"Price ({currency.upper()})",'date':'Date'})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        ohlc = get_ohlc_data(coin['id'], currency, days)
        if chart_type == "Candlestick":
            fig = go.Figure([go.Candlestick(
                x=ohlc['date'], open=ohlc['open'],
                high=ohlc['high'], low=ohlc['low'],
                close=ohlc['close']
            )])
        else:
            fig = go.Figure([go.Ohlc(
                x=ohlc['date'], open=ohlc['open'],
                high=ohlc['high'], low=ohlc['low'],
                close=ohlc['close']
            )])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

# ========================
# RENDER MAIN
# ========================
if df.empty:
    st.warning("Unable to load data.")
else:
    if st.session_state.selected_coin_id:
        display_coin_details()
    else:
        display_market_overview(df)

# ========================
# PRICE ALERTS & AUTO-REFRESH
# ========================
with st.sidebar:
    st.header("🔔 Alerts")
    if df.empty:
        st.info("No data for alerts.")
    else:
        watch = st.multiselect('Monitor Coins', df['name'].tolist())
        for c in watch:
            cd = df[df['name']==c].iloc[0]
            target = st.number_input(f"Alert for {c}", value=cd['current_price']*1.05, key=f"a_{c}")
            if cd['current_price'] >= target > 0:
                st.success(f"{c} hit {target}!")
                st.balloons()

if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()
