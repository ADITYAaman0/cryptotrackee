import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
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
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@400;700&family=Orbitron:wght@500&display=swap');

.central-header {
    font-family: 'Orbitron', sans-serif;
    font-size:3.5rem; 
    text-align:center; 
    background: linear-gradient(45deg, #4CAF50, #2196F3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom:20px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

/* … your other CSS … */

</style>
""", unsafe_allow_html=True)

# ========================
# FORMATTERS
# ========================
def abbreviate_number(num: float) -> str:
    """Turn 1_234_567 into '1.23M', etc."""
    for unit in ['', 'K', 'M', 'B', 'T', 'P']:
        if abs(num) < 1000.0:
            return f"{num:.2f}{unit}"
        num /= 1000.0
    return f"{num:.2f}E"

def format_currency(num: float, currency: str) -> str:
    """Format a raw number either as $1.23M (USD) or '1.23M EUR'."""
    abbr = abbreviate_number(num)
    if currency.lower() == 'usd':
        return f"${abbr}"
    return f"{abbr} {currency.upper()}"

# ========================
# WATCHLIST FUNCTIONALITY
# ========================
def init_watchlist():
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []

def toggle_watchlist(coin_id):
    wl = st.session_state.watchlist
    if coin_id in wl:
        wl.remove(coin_id)
    else:
        wl.append(coin_id)

def display_watchlist(df, currency):
    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Your Watchlist")
    if not st.session_state.watchlist:
        st.sidebar.info("Add coins to your watchlist using the star button ★")
        return

    watch_df = df[df['id'].isin(st.session_state.watchlist)]
    for _, coin in watch_df.iterrows():
        c1, c2 = st.sidebar.columns([1,4])
        with c1:
            st.image(coin['Logo'], width=40)
        with c2:
            pct = coin['24h %']
            clr = '#4CAF50' if pct>=0 else '#F44336'
            st.markdown(f"""
                <div class="watchlist-item">
                  <strong style="color:#FFF;">{coin['name']}</strong><br>
                  <span style="color:#CCC;">{coin['current_price']:,.4f} {currency.upper()}</span>
                  <span style="color:{clr}; margin-left:10px;">{pct:+.2f}%</span>
                </div>
            """, unsafe_allow_html=True)

# ========================
# DATA & HELPERS
# ========================
@st.cache_resource
def get_coingecko_client():
    return CoinGeckoAPI()

cg = get_coingecko_client()

def create_sparkline(data):
    if not isinstance(data, list) or len(data)<2:
        return ""
    series = pd.to_numeric(pd.Series(data), errors='coerce').dropna().tolist()
    if len(series)<2:
        return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(series))),
        y=series,
        mode='lines',
        line=dict(color='#4CAF50' if series[-1]>=series[0] else '#F44336', width=2)
    ))
    fig.update_layout(
        showlegend=False,
        xaxis_visible=False, yaxis_visible=False,
        margin=dict(t=0,b=0,l=0,r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        width=150, height=50
    )
    buf = BytesIO()
    fig.write_image(buf, format='png', engine='kaleido')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

@st.cache_data(ttl=30)
def load_market_data(vs_currency: str) -> pd.DataFrame:
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency,
            order='market_cap_desc',
            per_page=250,
            sparkline=True,
            price_change_percentage='24h,7d,30d'
        )
        df = pd.DataFrame(data)
        # compute the % columns
        df['24h %']  = pd.to_numeric(df.get('price_change_percentage_24h_in_currency'), errors='coerce').fillna(0.0)
        df['7d %']   = pd.to_numeric(df.get('price_change_percentage_7d_in_currency'), errors='coerce').fillna(0.0)
        df['30d %']  = pd.to_numeric(df.get('price_change_percentage_30d_in_currency'), errors='coerce').fillna(0.0)
        df['Symbol'] = df['symbol'].str.upper()
        df['Logo']   = df['image']
        df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0.0)
        df['market_cap']     = pd.to_numeric(df['market_cap'], errors='coerce').fillna(0)
        df['market_cap_rank']= pd.to_numeric(df['market_cap_rank'], errors='coerce').fillna(0).astype(int)
        # sparkline
        df['7d Sparkline'] = df['sparkline_in_7d'].apply(
            lambda s: create_sparkline(s['price']) if isinstance(s, dict) and 'price' in s else ""
        )
        return df
    except Exception as e:
        st.error(f"Error fetching market data: {e}")
        return pd.DataFrame()

# (You can add your get_historical_data, get_raw_ohlc_data, resample_ohlc_data here…)

# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    try:
        cur_list = cg.get_supported_vs_currencies()
        supported = sorted(c.lower() for c in cur_list)
        idx = supported.index('usd') if 'usd' in supported else 0
    except:
        supported = ['usd']; idx = 0
    currency = st.selectbox("Currency", supported, index=idx, key="currency_select")
    timeframe = st.selectbox("Movers Timeframe", ['24h','7d','30d'], index=1)
    refresh_interval = st.slider("Auto-Refresh (s)", 10, 300, 30)

# initialize & load
init_watchlist()
if 'selected_coin_id' not in st.session_state:
    st.session_state.selected_coin_id = None
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

df = load_market_data(currency)
display_watchlist(df, currency)

# ========================
# MAIN TABLE RENDERING
# ========================
def render_coins_table(df_to_show: pd.DataFrame, curr: str):
    if df_to_show.empty:
        st.write("No data available.")
        return

    specs = [0.3, 2.5, 1.5, 0.8, 1.8, 1.8, 0.5]
    headers = ["#", "Coin", f"Price ({curr.upper()})", "24h %", "Market Cap", "7d Sparkline", "★"]
    cols = st.columns(specs)
    for c, h in zip(cols, headers):
        c.markdown(f"<div class='coin-table-header'>{h}</div>", unsafe_allow_html=True)

    for idx, row in df_to_show.iterrows():
        c0, c1, c2, c3, c4, c5, c6 = st.columns(specs)
        coin_id = row['id']

        # star toggle
        with c6:
            icon = "★" if coin_id in st.session_state.watchlist else "☆"
            if st.button(icon, key=f"star_{coin_id}_{idx}", help="Watchlist"):
                toggle_watchlist(coin_id)
                st.experimental_rerun()

        c0.write(row['market_cap_rank'])

        # coin name + logo
        with c1:
            st.markdown(
                f"<img src='{row['Logo']}' width=20 style='vertical-align:middle;'/> "
                f"{row['name']} ({row['Symbol']})",
                unsafe_allow_html=True
            )

        # price
        c2.write(f"{row['current_price']:,.4f}")

        # 24h %
        pct = row['24h %']
        color = '#4CAF50' if pct >= 0 else '#F44336'
        c3.markdown(f"<span style='color:{color};'>{pct:+.2f}%</span>", unsafe_allow_html=True)

        # market cap
        c4.write(format_currency(row['market_cap'], curr))

        # sparkline
        if row['7d Sparkline']:
            c5.image(row['7d Sparkline'], use_column_width=True)
        else:
            c5.write("–")

# finally render!
render_coins_table(df, currency)
