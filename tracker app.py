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
# CUSTOM STYLING & LOTTIE
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
.central-header {font-size:3rem; font-weight:bold; text-align:center; color:#FFF; margin-bottom:20px;}
.stMetric {background:#262730; border-radius:12px; padding:20px; border:1px solid #4CAF50;}
.mover-header {font-size:1.5rem; font-weight:bold; color:#FFF; padding-bottom:10px; border-bottom:2px solid #4CAF50;}
.mover-row {display:flex; align-items:center; margin-bottom:10px;}
.mover-name {font-weight:bold; margin-left:10px;}
</style>
""", unsafe_allow_html=True)

# Header animation
with st.container():
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim: st_lottie(anim, height=200)
        st.markdown("<p class='central-header'>CRYPTO TRACKEE</p>", unsafe_allow_html=True)
    st.markdown("---")

# ========================
# DATA & HELPERS
# ========================
@st.cache_resource
def get_coingecko_client():
    return CoinGeckoAPI()

cg = get_coingecko_client()

# sparkline generator
def create_sparkline(data):
    if not data or len(data)<2: return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(data))), y=data, mode='lines',
        line=dict(color='#4CAF50' if data[-1]>=data[0] else '#F44336', width=2)
    ))
    fig.update_layout(showlegend=False, xaxis_visible=False, yaxis_visible=False,
                      margin=dict(t=0,b=0,l=0,r=0),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      width=150, height=50)
    buf = BytesIO(); fig.write_image(buf, format='png', engine='kaleido')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

@st.cache_data(ttl=60)
def load_market_data(vs_currency: str):
    data = cg.get_coins_markets(
        vs_currency=vs_currency, order='market_cap_desc', per_page=250,
        sparkline=True, price_change_percentage='24h,7d,30d'
    )
    df = pd.DataFrame(data)
    # percent-change cols
    df['24h %'] = df['price_change_percentage_24h_in_currency'].fillna(0)
    df['7d %']  = df['price_change_percentage_7d_in_currency'].fillna(0)
    df['30d %'] = df['price_change_percentage_30d_in_currency'].fillna(0)
    df['Symbol'] = df['symbol'].str.upper()
    df['Logo']   = df['image']
    df['7d Sparkline'] = df['sparkline_in_7d'].apply(lambda x: create_sparkline(x.get('price', [])))
    return df

@st.cache_data(ttl=3600)
def get_historical_data(coin_id: str, vs_currency: str, days: int = 30):
    chart = cg.get_coin_market_chart_by_id(coin_id, vs_currency, days)
    df = pd.DataFrame(chart['prices'], columns=['timestamp','price'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['date','price']]

@st.cache_data(ttl=3600)
def get_ohlc_data(coin_id: str, vs_currency: str, days: int = 30):
    # returns [timestamp, open, high, low, close]
    data = cg.get_coin_ohlc_by_id(coin_id, vs_currency, days)
    df = pd.DataFrame(data, columns=['timestamp','open','high','low','close'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['date','open','high','low','close']]

# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    supported = sorted(cg.get_supported_vs_currencies())
    cur_idx = supported.index('usd') if 'usd' in supported else 0
    currency = st.selectbox('Currency', supported, index=cur_idx)
    timeframe = st.selectbox('Movers Timeframe', ['24h','7d','30d'], index=1)
    refresh_interval = st.slider('Refresh Interval (s)', 10,300,60)

# state init
if 'selected_coin_id' not in st.session_state: st.session_state.selected_coin_id = None
if 'last_refresh' not in st.session_state: st.session_state.last_refresh = time.time()

# load main data
df = load_market_data(currency)

# ========================
# MOVERS DISPLAY
# ========================
def display_market_movers(df_mov, title, icon, pct_col):
    st.markdown(f"<p class='mover-header'>{icon} {title}</p>", unsafe_allow_html=True)
    for _,r in df_mov.iterrows():
        ch = r[pct_col]
        clr = '#4CAF50' if ch>=0 else '#F44336'
        st.markdown(f"""
            <div class='mover-row'>
              <img src='{r['Logo']}' width='30'>
              <span class='mover-name'>{r['name']}</span>
              <span style='flex-grow:1;text-align:right;color:{clr};font-weight:bold;'>
                {ch:+.2f}%
              </span>
            </div>
        """, unsafe_allow_html=True)

# ========================
# DETAIL VIEW
# ========================
def display_coin_details():
    sel = df[df['id']==st.session_state.selected_coin_id]
    if sel.empty:
        st.warning("Coin not available. Returning...")
        st.session_state.selected_coin_id = None
        st.rerun()
    coin = sel.iloc[0]
    st.subheader(f"{coin['name']} ({coin['Symbol']})")
    if st.button("⬅️ Back"): st.session_state.selected_coin_id=None; st.rerun()

    # choose chart type
    chart_type = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"])
    days = st.slider("History (days)", 7,90,30)

    if chart_type == "Line":
        hist = get_historical_data(coin['id'], currency, days)
        if not hist.empty:
            fig = px.line(hist, x='date', y='price', title=f"{coin['name']} Price (Last {days}d)",
                          labels={'price':f'Price ({currency.upper()})','date':'Date'})
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
    else:
        ohlc = get_ohlc_data(coin['id'], currency, days)
        if not ohlc.empty:
            if chart_type == "Candlestick":
                fig = go.Figure(data=[
                    go.Candlestick(
                        x=ohlc['date'], open=ohlc['open'], high=ohlc['high'],
                        low=ohlc['low'], close=ohlc['close']
                    )
                ])
            else:  # OHLC
                fig = go.Figure(data=[
                    go.Ohlc(
                        x=ohlc['date'], open=ohlc['open'], high=ohlc['high'],
                        low=ohlc['low'], close=ohlc['close']
                    )
                ])
            fig.update_layout(title=f"{coin['name']} {chart_type} Chart (Last {days}d)",
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

    # coin metrics
    st.subheader("Info & Metrics")
    c1,c2 = st.columns(2)
    c1.metric("Price", f"{coin['current_price']:,.4f} {currency.upper()}", f"{coin['24h %']:.2f}%")
    c2.metric("Market Cap", f"${coin['market_cap']:,}")
    c1.metric("24h Vol", f"${coin['total_volume']:,}")
    c2.metric("Rank", f"#{coin['market_cap_rank']}")

# ========================
# OVERVIEW
# ========================
def display_market_overview():
    # key metrics
    st.subheader("Key Metrics")
    b, e, t = st.columns(3)
    btc = df[df['Symbol']=='BTC'].iloc[0]
    eth = df[df['Symbol']=='ETH'].iloc[0]
    top24 = df.loc[df['24h %'].idxmax()]
    b.metric(f"BTC", f"{btc['current_price']:,.2f}", f"{btc['24h %']:.2f}%")
    e.metric(f"ETH", f"{eth['current_price']:,.2f}", f"{eth['24h %']:.2f}%")
    t.metric(f"Top 24h Gainer", f"{top24['name']} ({top24['24h %']:.2f}%)")
    st.markdown("---")

    # dynamic movers
    col_map = {'24h':'24h %','7d':'7d %','30d':'30d %'}
    pc = col_map[timeframe]
    st.subheader(f"Top Movers ({timeframe})")
    g = df.sort_values(pc, ascending=False).head(10)
    l = df.sort_values(pc, ascending=True).head(10)
    gc, lc = st.columns(2)
    with gc: display_market_movers(g, f"Gainers ({timeframe})", "🚀", pc)
    with lc: display_market_movers(l, f"Losers ({timeframe})", "📉", pc)
    st.markdown("---")

    # overview table
    st.subheader("Market Overview")
    tbl = df.head(50)
    hdrs = st.columns([0.5,2,1,2,1.5,2.5])
    for i,h in enumerate(["#","Coin","Price","24h %","Market Cap","7d Sparkline"]): hdrs[i].write(f"**{h}**")
    for _,r in tbl.iterrows():
        cols = st.columns([0.5,2,1,2,1.5,2.5])
        cols[0].write(r['market_cap_rank'])
        if cols[1].button(f"{r['name']} ({r['Symbol']})", key=r['id']): st.session_state.selected_coin_id=r['id']; st.rerun()
        cols[2].write(f"{r['current_price']:,.4f}")
        clr = '#4CAF50' if r['24h %']>=0 else '#F44336'
        cols[3].markdown(f"<b style='color:{clr};'>{r['24h %']:+.2f}%</b>", unsafe_allow_html=True)
        cols[4].write(f"${r['market_cap']:,}")
        if r['7d Sparkline']: cols[5].markdown(f"<img src='{r['7d Sparkline']}'>", unsafe_allow_html=True)

# ================
# MAIN
# ================
if df.empty:
    st.warning("Unable to load data.")
else:
    if st.session_state.selected_coin_id:
        display_coin_details()
    else:
        display_market_overview()

# ========================
# PRICE ALERTS
# ========================
with st.sidebar:
    st.header("🔔 Alerts")
    if not df.empty:
        watch = st.multiselect('Monitor Coins', df['name'].tolist())
        for c in watch:
            cd = df[df['name']==c].iloc[0]
            curr = cd['current_price']
            target = st.number_input(f"Alert for {c}", value=float(curr*1.05), key=f"a_{c}")
            if curr>=target>0:
                st.success(f"{c} hit {target}!")
                st.balloons()
    else:
        st.info("No data for alerts.")

# auto-refresh
if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()
