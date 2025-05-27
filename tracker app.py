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

.stMetric {
    background:#1a1a2e; 
    border-radius:12px; 
    padding:20px; 
    border:1px solid #4CAF50;
    box-shadow: 0 4px 8px rgba(76,175,80,0.2);
}

.mover-header {
    font-family: 'Kanit', sans-serif;
    font-size:1.8rem; 
    color:#FFF; 
    padding-bottom:10px; 
    border-bottom:2px solid #4CAF50;
}

.watchlist-item {
    padding: 12px;
    margin: 8px 0;
    border-radius: 8px;
    background: rgba(76,175,80,0.15);
    transition: transform 0.2s;
}

.watchlist-item:hover {
    transform: translateX(5px);
    background: rgba(76,175,80,0.25);
}

.watchlist-price {
    font-family: 'Kanit', sans-serif;
    color: #4CAF50;
    font-size: 1.1rem;
}

.coin-table-header {
    font-family: 'Kanit', sans-serif;
    color: #4CAF50 !important;
    font-size: 1.2rem;
}

.coin-table-row {
    border-bottom: 1px solid rgba(76,175,80,0.2);
    padding: 12px 0;
}

.star-button {
    color: #FFD700 !important;
    font-size: 1.4rem;
    transition: all 0.3s;
}

.star-button:hover {
    transform: scale(1.2);
    cursor: pointer;
}

.js-plotly-plot .plotly, .js-plotly-plot .plotly div {
    background: #0a0a1a !important;
}

.stTextInput > div > div > input {
    border-radius: 25px;
    border: 2px solid #4CAF50;
    padding: 10px 15px;
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    transition: 0.3s;
    color: #E0E0E0;
    background-color: #1A1A1A;
}
</style>
""", unsafe_allow_html=True)

# ========================
# WATCHLIST FUNCTIONALITY
# ========================
def init_watchlist():
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []

def toggle_watchlist(coin_id):
    if coin_id in st.session_state.watchlist:
        st.session_state.watchlist.remove(coin_id)
    else:
        st.session_state.watchlist.append(coin_id)

def display_watchlist(df, currency):
    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Your Watchlist")
    
    if not st.session_state.watchlist:
        st.sidebar.info("Add coins to your watchlist using the star button ★")
        return
    
    watchlist_coins = df[df['id'].isin(st.session_state.watchlist)]
    
    for _, coin in watchlist_coins.iterrows():
        col1, col2 = st.sidebar.columns([1,4])
        with col1:
            st.image(coin['Logo'], width=40)
        with col2:
            st.markdown(f"""
            <div class="watchlist-item">
                <div style="font-weight:bold; color:#FFF;">{coin['name']}</div>
                <div class="watchlist-price">
                    {coin['current_price']:,.4f} {currency.upper()}
                    <span style="color:{'#4CAF50' if coin['24h %'] >=0 else '#F44336'}; margin-left:12px;">
                        {coin['24h %']:+.2f}%
                    </span>
                </div>
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
    if not data or not isinstance(data, list) or len(data)<2: return ""
    try:
        numeric_data = pd.to_numeric(pd.Series(data), errors='coerce').dropna().tolist()
        if len(numeric_data) < 2: return ""

        fig = go.Figure(go.Scatter(
            x=list(range(len(numeric_data))), y=numeric_data, mode='lines',
            line=dict(color='#4CAF50' if numeric_data[-1]>=numeric_data[0] else '#F44336', width=2)
        ))
        fig.update_layout(showlegend=False, xaxis_visible=False, yaxis_visible=False,
                          margin=dict(t=0,b=0,l=0,r=0),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          width=150, height=50)
        buf = BytesIO(); fig.write_image(buf, format='png', engine='kaleido')
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    except Exception:
        return ""

@st.cache_data(ttl=30)
def load_market_data(vs_currency: str):
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency, order='market_cap_desc', per_page=250,
            sparkline=True, price_change_percentage='24h,7d,30d'
        )
        if not data:
            return pd.DataFrame()
        df_loaded = pd.DataFrame(data)
        if df_loaded.empty:
            return pd.DataFrame()

        df_loaded['24h %'] = pd.to_numeric(df_loaded.get('price_change_percentage_24h_in_currency'), errors='coerce').fillna(0.0)
        df_loaded['7d %']  = pd.to_numeric(df_loaded.get('price_change_percentage_7d_in_currency'), errors='coerce').fillna(0.0)
        df_loaded['30d %'] = pd.to_numeric(df_loaded.get('price_change_percentage_30d_in_currency'), errors='coerce').fillna(0.0)
        df_loaded['Symbol'] = df_loaded.get('symbol', pd.Series(dtype='object')).astype(str).str.upper().fillna('N/A')
        df_loaded['Logo']   = df_loaded.get('image', pd.Series(dtype='object')).astype(str).fillna('')
        df_loaded['id']     = df_loaded.get('id', pd.Series(dtype='object')).astype(str).fillna('unknown')
        df_loaded['name']   = df_loaded.get('name', pd.Series(dtype='object')).astype(str).fillna('Unknown Coin')
        df_loaded['current_price'] = pd.to_numeric(df_loaded.get('current_price'), errors='coerce').fillna(0.0)
        df_loaded['market_cap'] = pd.to_numeric(df_loaded.get('market_cap'), errors='coerce').fillna(0)
        df_loaded['total_volume'] = pd.to_numeric(df_loaded.get('total_volume'), errors='coerce').fillna(0)
        df_loaded['market_cap_rank'] = pd.to_numeric(df_loaded.get('market_cap_rank'), errors='coerce')

        if 'sparkline_in_7d' in df_loaded.columns:
            df_loaded['7d Sparkline'] = df_loaded['sparkline_in_7d'].apply(
                lambda x: create_sparkline(x.get('price', [])) if isinstance(x, dict) and x.get('price') else ""
            )
        else:
            df_loaded['7d Sparkline'] = ""
            
        return df_loaded
    except Exception as e:
        st.error(f"Error fetching or processing market data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_data(coin_id: str, vs_currency: str, days: int = 30):
    try:
        chart = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
        if not chart or 'prices' not in chart: return pd.DataFrame()
        df_hist = pd.DataFrame(chart['prices'], columns=['timestamp','price'])
        df_hist['date'] = pd.to_datetime(df_hist['timestamp'], unit='ms')
        df_hist['price'] = pd.to_numeric(df_hist['price'], errors='coerce')
        return df_hist[['date','price']].dropna()
    except Exception as e:
        st.error(f"Error fetching historical data for {coin_id}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_raw_ohlc_data_from_coingecko(coin_id: str, vs_currency: str, days: int):
    try:
        data_ohlc = cg.get_coin_ohlc_by_id(id=coin_id, vs_currency=vs_currency, days=days)
        if not data_ohlc: return pd.DataFrame()
        df_ohlc = pd.DataFrame(data_ohlc, columns=['timestamp','open','high','low','close'])
        df_ohlc['date'] = pd.to_datetime(df_ohlc['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close']:
            df_ohlc[col] = pd.to_numeric(df_ohlc[col], errors='coerce')
        return df_ohlc[['date','open','high','low','close']].dropna()
    except Exception as e:
        st.error(f"Error fetching OHLC data for {coin_id}: {e}")
        return pd.DataFrame()

def resample_ohlc_data(df_ohlc_1min: pd.DataFrame, interval: str) -> pd.DataFrame:
    if df_ohlc_1min.empty or not all(col in df_ohlc_1min.columns for col in ['date', 'open', 'high', 'low', 'close']):
        return pd.DataFrame()

    df_resampled = df_ohlc_1min.set_index('date')
    
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }
    
    try:
        resampled_df = df_resampled.resample(interval).apply(ohlc_dict).dropna()
        resampled_df = resampled_df.reset_index()
        return resampled_df
    except Exception as e:
        st.error(f"Error resampling OHLC data to {interval}: {e}")
        return pd.DataFrame()

# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    try:
        supported_currencies_list = cg.get_supported_vs_currencies()
        if supported_currencies_list:
            supported = sorted([str(c).lower() for c in supported_currencies_list])
            cur_idx = supported.index('usd') if 'usd' in supported else 0
        else:
            supported = ['usd']  
            cur_idx = 0
            st.warning("Could not fetch supported currencies. Using USD.")
    except Exception:
        supported = ['usd']  
        cur_idx = 0
        st.warning(f"Could not fetch supported currencies. Using USD.")
        
    currency = st.selectbox('Currency', supported, index=cur_idx, key="currency_select")
    timeframe = st.selectbox('Movers Timeframe', ['24h','7d','30d'], index=1, key="timeframe_select")  
    refresh_interval = st.slider('Auto-Refresh Interval (s)', 10, 300, 30, key="refresh_slider")

# Initialize watchlist
init_watchlist()

# ========================
# SESSION STATE INIT
# ========================
if 'selected_coin_id' not in st.session_state: st.session_state.selected_coin_id = None
if 'last_refresh' not in st.session_state: st.session_state.last_refresh = time.time()
if 'search_query' not in st.session_state: st.session_state.search_query = ""

# Load main data
df = load_market_data(currency)

# Display watchlist in sidebar
display_watchlist(df, currency)

# ========================
# MAIN DISPLAY LOGIC
# ========================
def render_coins_table(data_df_to_render, currency_symbol_for_table):
    if data_df_to_render.empty:
        return

    header_cols_spec = [0.3, 2.5, 1.5, 0.8, 1.8, 1.8, 0.5]
    header_cols = st.columns(header_cols_spec)
    headers = ["#", "Coin", f"Price ({currency_symbol_for_table.upper()})", "24h %", "Market Cap", "7d Sparkline", "★"]
    
    for col, header_text in zip(header_cols, headers):
        col.markdown(f"<div class='coin-table-header'>{header_text}</div>", unsafe_allow_html=True)

    for index, r_row_table in data_df_to_render.iterrows():
        row_cols = st.columns(header_cols_spec)
        coin_id = str(r_row_table.get('id', f"unknown_{index}"))
        
        # Star button column
        with row_cols[-1]:
            star_icon = "★" if coin_id in st.session_state.watchlist else "☆"
            if st.button(star_icon, key=f"star_{coin_id}_{index}", help="Add to watchlist"):
                toggle_watchlist(coin_id)
                st.rerun()

        row_cols[0].write(str(r_row_table.get('market_cap_rank', 'N/A')))
        
        coin_name_tbl_render = str(r_row_table.get('name', 'N/A'))
        coin_symbol_tbl_render = str(r_row_table.get('Symbol', 'N/A'))
        button_key_render = f"select_TABLE_{coin_id}_{index}"
        logo_url_render = r_row_table.get('Logo', '')
        
        if logo_url_render:
            row_cols[1].markdown(
                f"<div style='display:flex; align-items:center;'>"
                f"<img src='{logo_url_render}' width='20' height='20' style='margin-right:5px; vertical-align:middle;'>"
                f"<button style='background:none; border:none; padding:0; cursor:pointer; color:inherit; font-size:inherit; text-align:left;' key='{button_key_render}' "
                f"onclick=\"document.getElementById('select_TABLE_{coin_id}_{index}').click();\">"
                f"{coin_name_tbl_render} ({coin_symbol_tbl_render})"
                f"</button>"
                f"</div>",
                unsafe_allow_html=True
            )
            if row_cols[1].button(" ", key=button_key_render + "_hidden", use_container_width=True):
                st.session_state.selected_coin_id = coin_id
                st.session_state.search_query = ""
                st.rerun()
        else:
            if row_cols[1].button(f"{coin_name_tbl_render} ({coin_symbol_tbl_render})", key=button_key_render):
                st.session_state.selected_coin_id = coin_id
                st.session_state.search_query = ""
                st.rerun()
                
        current_price_val = r_row_table.get('current_price', 0.0)
        row_cols[2].write(f"{current_price_val:,.4f}")
        
        change_24h = r_row_table.get('24h %', 0.0)
        clr = '#4CAF50' if change_24h >= 0 else '#F44336'
        row_cols[3].markdown(f"<div style='color:{clr}; font-weight:bold; text-align:left;'>{change_24h:+.2f}%</div>", unsafe_allow_html=True)
        
        market_cap = r_row_table.get('market_cap', 0)
        row_cols[4].write(f"${market_cap:,}" if currency.lower() == 'usd'
