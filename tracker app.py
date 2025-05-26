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
/* Attractive Search Bar Styling */
.stTextInput > div > div > input {
    border-radius: 25px; /* More rounded corners */
    border: 2px solid #4CAF50; /* Green border */
    padding: 10px 15px; /* More padding */
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); /* Subtle shadow */
    transition: 0.3s; /* Smooth transition for hover/focus */
    color: #E0E0E0; /* Text color */
    background-color: #1A1A1A; /* Darker background */
}
.stTextInput > div > div > input:focus {
    border-color: #2196F3; /* Blue on focus */
    box-shadow: 0 4px 12px 0 rgba(33,150,243,0.3); /* Blue shadow on focus */
}
.stTextInput label {
    font-weight: bold;
    color: #E0E0E0;
    font-size: 1.1rem; /* Slightly larger label */
    margin-bottom: 5px;
    display: block; /* Make label a block element for spacing */
}
/* Style for the "Clear Search" button */
.stButton > button {
    border-radius: 8px;
    border: 1px solid #F44336; /* Red border */
    background-color: #F44336; /* Red background */
    color: white;
    padding: 8px 15px;
    font-weight: bold;
    transition: 0.2s;
}
.stButton > button:hover {
    background-color: #D32F2F; /* Darker red on hover */
    border-color: #D32F2F;
}

/* Custom styling for chart info metrics */
.chart-info-metric {
    font-size: 1.1rem;
    color: #E0E0E0;
    margin-right: 15px;
    display: inline-block;
}
.chart-info-value {
    font-weight: bold;
}
.change-positive {
    color: #4CAF50;
}
.change-negative {
    color: #F44336;
}
</style>
""", unsafe_allow_html=True)

# Header animation
with st.container():
    col1_header, col2_header, col3_header = st.columns([1,3,1])
    with col2_header:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim: st_lottie(anim, height=200, key="header_animation")
        st.markdown("<p class='central-header'>CRYPTO TRACKEE</p>", unsafe_allow_html=True)
    st.markdown("---")

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

@st.cache_data(ttl=30) # Reduced from 60 to 30 seconds for slightly 'more live' feel
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

@st.cache_data(ttl=3600) # 1 hour
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

# Modified: This function now primarily fetches 1-minute data for intraday,
# or daily/hourly for longer timeframes.
@st.cache_data(ttl=60) # Set TTL to 60 seconds for 1-minute data to be somewhat 'live'
def get_raw_ohlc_data_from_coingecko(coin_id: str, vs_currency: str, days: int):
    """
    Fetches raw OHLC data from CoinGecko.
    days=1 gives 1-minute data for the last 24 hours.
    Other days parameters give hourly or daily data.
    """
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
    """
    Resamples 1-minute OHLC data to a specified interval (e.g., '5min', '1H').
    Requires 'date' column to be datetime and set as index.
    """
    if df_ohlc_1min.empty or not all(col in df_ohlc_1min.columns for col in ['date', 'open', 'high', 'low', 'close']):
        return pd.DataFrame()

    df_resampled = df_ohlc_1min.set_index('date')
    
    # Check if the data frequency is already lower than or equal to the requested interval
    # For simplicity, we'll assume we're usually resampling UP (e.g., 1min to 5min)
    # If the base data is already hourly and we ask for 15min, resampling won't work correctly.
    # CoinGecko's 'days=1' ensures 1-minute data, so this resampling logic should be fine.

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
    
    # Default refresh interval set to a lower value (e.g., 30 seconds)
    refresh_interval = st.slider('Auto-Refresh Interval (s)', 10, 300, 30, key="refresh_slider")

# ========================
# SESSION STATE INITIALIZATION
# ========================
if 'selected_coin_id' not in st.session_state: st.session_state.selected_coin_id = None
if 'last_refresh' not in st.session_state: st.session_state.last_refresh = time.time()
if 'search_query' not in st.session_state: st.session_state.search_query = ""


# Load main data
df = load_market_data(currency)

# ========================
# HELPER FUNCTIONS FOR DISPLAY
# ========================
def display_market_movers(df_mov, title, icon, pct_col_name):
    st.markdown(f"<p class='mover-header'>{icon} {title}</p>", unsafe_allow_html=True)
    if df_mov.empty or pct_col_name not in df_mov.columns:
        st.caption(f"No data available for {title.lower()}.")
        return
    for _,r_mov in df_mov.iterrows():
        ch = r_mov.get(pct_col_name, 0.0)  
        ch = ch if pd.notnull(ch) else 0.0
        clr = '#4CAF50' if ch>=0 else '#F44336'
        logo_url = r_mov.get('Logo', '')
        coin_name_mov = r_mov.get('name', 'N/A')
        st.markdown(f"""
            <div class='mover-row'>
                <img src='{logo_url}' width='30' alt='{coin_name_mov} logo' style='vertical-align:middle; margin-right:5px;'>
                <span class='mover-name'>{coin_name_mov}</span>
                <span style='flex-grow:1;text-align:right;color:{clr};font-weight:bold;'>
                    {ch:+.2f}%
                </span>
            </div>
        """, unsafe_allow_html=True)

def render_coins_table(data_df_to_render, currency_symbol_for_table):
    if data_df_to_render.empty:
        return

    header_cols_spec = [0.4, 2.2, 1.5, 0.8, 1.8, 1.8]  
    header_cols = st.columns(header_cols_spec)
    headers = ["#", "Coin", f"Price ({currency_symbol_for_table.upper()})", "24h %", "Market Cap", "7d Sparkline"]
    for col, header_text in zip(header_cols, headers):
        col.markdown(f"**{header_text}**")

    for index, r_row_table in data_df_to_render.iterrows():
        row_cols = st.columns(header_cols_spec)  
        
        if not isinstance(r_row_table, pd.Series):
            continue

        row_cols[0].write(str(r_row_table.get('market_cap_rank', 'N/A')))
        
        coin_id_tbl_render = str(r_row_table.get('id', f"unknown_TABLE_{index}"))
        coin_name_tbl_render = str(r_row_table.get('name', 'N/A'))
        coin_symbol_tbl_render = str(r_row_table.get('Symbol', 'N/A'))
        
        button_key_render = f"select_TABLE_{coin_id_tbl_render}_{index}"  
        coin_label_render = f"{coin_name_tbl_render} ({coin_symbol_tbl_render})"

        # Using a small image for the logo next to the button
        logo_url_render = r_row_table.get('Logo', '')
        if logo_url_render:
            row_cols[1].markdown(
                f"<div style='display:flex; align-items:center;'>"
                f"<img src='{logo_url_render}' width='20' height='20' style='margin-right:5px; vertical-align:middle;'>"
                f"<button style='background:none; border:none; padding:0; cursor:pointer; color:inherit; font-size:inherit; text-align:left;' key='{button_key_render}' "
                f"onclick=\"document.getElementById('select_TABLE_{coin_id_tbl_render}_{index}').click();\">"
                f"{coin_label_render}"
                f"</button>"
                f"</div>",
                unsafe_allow_html=True
            )
            # A hidden button to trigger the session state change, as direct JS calls from markdown are limited
            if row_cols[1].button(" ", key=button_key_render + "_hidden", help=f"View details for {coin_name_tbl_render}", use_container_width=True):
                st.session_state.selected_coin_id = coin_id_tbl_render  
                st.session_state.search_query = "" # Clear search when navigating to detail view
                st.rerun()
        else:
            if row_cols[1].button(coin_label_render, key=button_key_render, help=f"View details for {coin_name_tbl_render}"):
                st.session_state.selected_coin_id = coin_id_tbl_render  
                st.session_state.search_query = "" # Clear search when navigating to detail view
                st.rerun()
            
        current_price_val_row_render = r_row_table.get('current_price', 0.0); current_price_val_row_render = current_price_val_row_render if pd.notnull(current_price_val_row_render) else 0.0
        row_cols[2].write(f"{current_price_val_row_render:,.4f}")
        
        change_24h_tbl_render = r_row_table.get('24h %', 0.0); change_24h_tbl_render = change_24h_tbl_render if pd.notnull(change_24h_tbl_render) else 0.0
        clr_tbl_render = '#4CAF50' if change_24h_tbl_render >= 0 else '#F44336'
        row_cols[3].markdown(f"<div style='color:{clr_tbl_render}; font-weight:bold; text-align:left;'>{change_24h_tbl_render:+.2f}%</div>", unsafe_allow_html=True)
        
        market_cap_val_row_render = r_row_table.get('market_cap', 0); market_cap_val_row_render = market_cap_val_row_render if pd.notnull(market_cap_val_row_render) else 0
        row_cols[4].write(f"${market_cap_val_row_render:,}" if currency_symbol_for_table.lower() == 'usd' else f"{market_cap_val_row_render:,} {currency_symbol_for_table.upper()}")
        
        sparkline_html_render = r_row_table.get('7d Sparkline', '')
        if sparkline_html_render:
            row_cols[5].markdown(f"<img src='{sparkline_html_render}' alt='7d sparkline for {coin_name_tbl_render}'>", unsafe_allow_html=True)
        else:
            row_cols[5].caption("N/A")
        st.markdown("<hr style='margin-top:0.3rem; margin-bottom:0.3rem; border-top: 1px solid #333;'>", unsafe_allow_html=True)

# ========================
# DETAIL VIEW
# ========================
def display_coin_details():
    selected_id = st.session_state.selected_coin_id
    if selected_id is None or 'id' not in df.columns:
        st.warning("Coin data or selection is invalid. Returning to overview.")
        st.session_state.selected_coin_id = None  
        st.rerun()
        return

    sel = df[df['id'] == selected_id]
    if sel.empty:
        st.warning(f"Selected coin (ID: {selected_id}) not found. Returning to overview.")
        st.session_state.selected_coin_id = None
        st.rerun()
        return  
        
    coin = sel.iloc[0]
    coin_name_detail = coin.get('name', 'N/A')
    coin_symbol_detail = coin.get('Symbol', 'N/A')
    coin_id_detail = coin.get('id', 'unknown')
    coin_logo_detail = coin.get('Logo', '')


    # Top bar for coin name, symbol, logo, and metrics
    top_chart_cols = st.columns([0.1, 1, 0.2, 0.2, 0.2, 0.2, 0.2, 0.5])
    with top_chart_cols[0]:
        if coin_logo_detail:
            st.image(coin_logo_detail, width=40)
    with top_chart_cols[1]:
        st.markdown(f"**<span style='font-size:1.5rem;'>{coin_name_detail}</span>** <span style='color:#AAA;'>{coin_symbol_detail.upper()}</span>", unsafe_allow_html=True)
    
    # Get latest OHLC data for display in the top bar (1-minute granularity)
    ohlc_for_metrics = get_raw_ohlc_data_from_coingecko(coin_id_detail, currency, days=1) 
    latest_price_info = ohlc_for_metrics.iloc[-1] if not ohlc_for_metrics.empty else {}
    
    current_price_val = coin.get('current_price', 0.0)
    change_24h_val = coin.get('24h %', 0.0)
    change_color_class = "change-positive" if change_24h_val >= 0 else "change-negative"

    top_chart_cols[2].markdown(f"<span class='chart-info-metric'>Price: <span class='chart-info-value'>{current_price_val:,.4f} {currency.upper()}</span></span>", unsafe_allow_html=True)
    top_chart_cols[3].markdown(f"<span class='chart-info-metric'>24h %: <span class='chart-info-value {change_color_class}'>{change_24h_val:+.2f}%</span></span>", unsafe_allow_html=True)

    if not ohlc_for_metrics.empty:
        top_chart_cols[4].markdown(f"<span class='chart-info-metric'>O: <span class='chart-info-value'>{latest_price_info.get('open',0.0):,.4f}</span></span>", unsafe_allow_html=True)
        top_chart_cols[5].markdown(f"<span class='chart-info-metric'>H: <span class='chart_info-value'>{latest_price_info.get('high',0.0):,.4f}</span></span>", unsafe_allow_html=True)
        top_chart_cols[6].markdown(f"<span class='chart-info-metric'>L: <span class='chart-info-value'>{latest_price_info.get('low',0.0):,.4f}</span></span>", unsafe_allow_html=True)
        top_chart_cols[7].markdown(f"<span class='chart-info-metric'>C: <span class='chart-info-value'>{latest_price_info.get('close',0.0):,.4f}</span></span>", unsafe_allow_html=True)

    st.markdown("---") # Separator below the top info bar

    # Back button and timeframe selector
    chart_controls_cols = st.columns([0.5, 3, 1])
    with chart_controls_cols[0]:
        if st.button("⬅️ Back to Overview", key=f"back_button_{coin_id_detail}"):  
            st.session_state.selected_coin_id=None
            st.session_state.search_query = "" # Clear search when going back from detail
            st.rerun()
    
    with chart_controls_cols[1]:
        # Updated timeframe options to include intraday and longer periods
        timeframe_options = ['1m', '5m', '10m', '15m', '30m', '1h', '4h', '1D', '7D', '1M', '3M', '6M', '1Y', 'MAX']
        
        # Set default index carefully. If '1D' is in options, use its index.
        default_timeframe_index = timeframe_options.index('1D') if '1D' in timeframe_options else 0

        selected_timeframe = st.radio(
            "Select Timeframe",
            options=timeframe_options,
            index=default_timeframe_index, # Default to 1 Day (1-min candles)
            horizontal=True,
            key=f"chart_timeframe_{coin_id_detail}"
        )

    with chart_controls_cols[2]:
        chart_type = st.selectbox("Chart Type", ["Candlestick","Line","OHLC"], index=0, key=f"chart_type_{coin_id_detail}") # Default to Candlestick

    # Chart rendering logic
    fig_data_loaded = False
    ohlc_data_for_chart = pd.DataFrame()
    line_data_for_chart = pd.DataFrame()

    # Define CoinGecko 'days' mapping for OHLC/Historical API calls
    coingecko_days_map_ohlc = {
        '1D': 1, # 1-min interval
        '7D': 7, # hourly interval
        '1M': 30, # daily interval
        '3M': 90, # daily interval
        '6M': 180, # daily interval
        '1Y': 365, # daily interval
        'MAX': 365 # daily interval (capped at 365 for detailed OHLC)
    }

    # First, fetch the base data (1-min for intraday, or direct for longer periods)
    if selected_timeframe in ['1m', '5m', '10m', '15m', '30m', '1h', '4h', '1D']:
        # For all intraday and '1D' (which means 1-minute data for 24h), fetch the raw 1-minute data
        raw_1min_ohlc = get_raw_ohlc_data_from_coingecko(coin_id_detail, currency, days=1)
        if not raw_1min_ohlc.empty:
            if selected_timeframe == '1m' or selected_timeframe == '1D':
                ohlc_data_for_chart = raw_1min_ohlc
            else: # Resample for other intraday intervals
                interval_map_pandas = {
                    '5m': '5min', '10m': '10min', '15m': '15min', '30m': '30min',
                    '1h': '1H', '4h': '4H'
                }
                resampling_interval = interval_map_pandas.get(selected_timeframe)
                if resampling_interval:
                    ohlc_data_for_chart = resample_ohlc_data(raw_1min_ohlc, resampling_interval)
                else:
                    st.info(f"Unsupported resampling interval: {selected_timeframe}")
        else:
            st.info(f"Not enough 1-minute data to generate {selected_timeframe} chart for {coin_name_detail}.")
            
    elif selected_timeframe in ['7D', '1M', '3M', '6M', '1Y', 'MAX']:
        # For longer timeframes, use CoinGecko's default hourly/daily intervals directly
        days_param = coingecko_days_map_ohlc.get(selected_timeframe)
        if days_param:
            ohlc_data_for_chart = get_raw_ohlc_data_from_coingecko(coin_id_detail, currency, days=days_param)
        else:
            st.info(f"Invalid timeframe selection for direct OHLC fetch: {selected_timeframe}")

    # Now, plot the chart based on the prepared data
    if chart_type in ["Candlestick", "OHLC"]:
        if not ohlc_data_for_chart.empty and all(col in ohlc_data_for_chart.columns for col in ['open', 'high', 'low', 'close']):
            if chart_type == "Candlestick":
                fig = go.Figure(data=[
                    go.Candlestick(
                        x=ohlc_data_for_chart['date'], 
                        open=ohlc_data_for_chart['open'], 
                        high=ohlc_data_for_chart['high'], 
                        low=ohlc_data_for_chart['low'], 
                        close=ohlc_data_for_chart['close'],
                        increasing_line_color='#4CAF50', # Green for increasing
                        decreasing_line_color='#F44336' # Red for decreasing
                    )
                ])
            else: # OHLC
                fig = go.Figure(data=[
                    go.Ohlc(
                        x=ohlc_data_for_chart['date'], 
                        open=ohlc_data_for_chart['open'], 
                        high=ohlc_data_for_chart['high'], 
                        low=ohlc_data_for_chart['low'], 
                        close=ohlc_data_for_chart['close'],
                        increasing_line_color='#4CAF50', # Green for increasing
                        decreasing_line_color='#F44336' # Red for decreasing
                    )
                ])
            
            fig.update_layout(
                title={
                    'text': f"{coin_name_detail} {chart_type} Chart ({selected_timeframe} intervals)",
                    'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'
                },
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font_color="#E0E0E0", # Light grey font color
                title_font_color="#FFFFFF",
                xaxis=dict(
                    showgrid=False, 
                    color="#E0E0E0", # X-axis labels color
                    linecolor="#444", # X-axis line color
                    gridcolor='rgba(128,128,128,0.1)' # Lighter grid lines
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(128,128,128,0.1)', # Lighter grid lines
                    color="#E0E0E0", # Y-axis labels color
                    linecolor="#444", # Y-axis line color
                    side='right' # Y-axis on the right
                ),
                hovermode="x unified" # Enable unified hover for better data display on hover
            )
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
        else:
            st.info(f"No OHLC data available for {coin_name_detail} for the selected '{selected_timeframe}' timeframe.")
    elif chart_type == "Line":
        # For line charts, CoinGecko's historical data endpoint (`get_coin_market_chart_by_id`)
        # provides price data which is generally at a higher frequency for shorter `days` params.
        # We'll use this directly for line charts.

        # Map selected_timeframe to days parameter for get_historical_data
        hist_days_param = 1 # Default for intraday line chart
        if selected_timeframe in ['7D', '1M', '3M', '6M', '1Y', 'MAX']:
            hist_days_param = coingecko_days_map_ohlc.get(selected_timeframe, 1) # Reuse map, default to 1 day if not found
        
        line_data_for_chart = get_historical_data(coin_id_detail, currency, days=hist_days_param)
        
        if not line_data_for_chart.empty and 'price' in line_data_for_chart.columns and not line_data_for_chart['price'].isna().all():
            fig = px.line(line_data_for_chart, x='date', y='price', title=f"{coin_name_detail} Price ({selected_timeframe} intervals)",
                          labels={'price':f'Price ({currency.upper()})','date':'Date'})
            fig.update_layout(
                title={
                    'text': f"{coin_name_detail} Price ({selected_timeframe} intervals)",
                    'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'
                },
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font_color="#E0E0E0", 
                title_font_color="#FFFFFF",
                xaxis=dict(
                    showgrid=False, 
                    color="#E0E0E0", 
                    linecolor="#444",
                    gridcolor='rgba(128,128,128,0.1)'
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(128,128,128,0.1)', 
                    color="#E0E0E0",
                    linecolor="#444",
                    side='right'
                ),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
        else:
            st.info(f"No line chart data available for {coin_name_detail} for the selected '{selected_timeframe}' timeframe.")
            
    if not fig_data_loaded:
        st.info(f"No chart data to display for {coin_name_detail} for the selected period or type. CoinGecko API might not provide this specific interval directly, or there isn't enough historical data.")

    st.markdown("---") # Separator below the chart

    st.subheader("Info & Metrics")
    c1_detail, c2_detail = st.columns(2)
    
    market_cap_val = coin.get('market_cap', 0); market_cap_val = market_cap_val if pd.notnull(market_cap_val) else 0
    total_volume_val = coin.get('total_volume', 0); total_volume_val = total_volume_val if pd.notnull(total_volume_val) else 0
    
    c1_detail.metric("Market Cap", f"${market_cap_val:,}" if currency.lower() == 'usd' else f"{market_cap_val:,} {currency.upper()}")
    c2_detail.metric("24h Vol", f"${total_volume_val:,}" if currency.lower() == 'usd' else f"{total_volume_val:,} {currency.upper()}")
    c1_detail.metric("Rank", f"#{coin.get('market_cap_rank', 'N/A')}")


# ========================
# MARKET OVERVIEW (Main Display Logic with Search)
# ========================
def display_market_overview():
    # Search Bar - spans across the content area
    search_query_input = st.text_input(
        "🔍 Search Coins (by Name or Symbol)",
        value=st.session_state.get("search_query", ""),
        placeholder="E.g., Bitcoin or BTC",
        key="search_bar_input_main_page"
    )

    if search_query_input != st.session_state.get("search_query", ""):
        st.session_state.search_query = search_query_input
        st.rerun()

    search_active = bool(st.session_state.get("search_query", "").strip())

    if search_active:
        st.markdown("---")
        
        # Back option (Clear Search)
        st.button("⬅️ Clear Search", key="clear_search_button_active", on_click=lambda: st.session_state.update(search_query=""), help="Click to clear the search and return to main overview.")
        
        st.subheader(f"Search Results for \"{st.session_state.search_query}\"")
        
        query = st.session_state.search_query.lower()
        
        if df.empty:
            st.warning("Market data is not available for searching.")
            return

        df_searchable = df.copy()

        if 'name' not in df_searchable.columns: df_searchable['name'] = 'N/A'
        if 'Symbol' not in df_searchable.columns: df_searchable['Symbol'] = 'N/A'

        df_searchable['name_lower'] = df_searchable['name'].astype(str).str.lower()
        df_searchable['symbol_lower'] = df_searchable['Symbol'].astype(str).str.lower()

        search_results_df = df_searchable[
            df_searchable['name_lower'].str.contains(query, na=False) |
            df_searchable['symbol_lower'].str.contains(query, na=False)
        ]

        if search_results_df.empty:
            st.info(f"No coins found matching \"{st.session_state.search_query}\".")
        else:
            st.markdown(f"Found **{len(search_results_df)}** matching coin(s). Displaying all results.")
            render_coins_table(search_results_df, currency)  

    else: # Default view (no active search)
        st.subheader("Key Metrics")
        b_col, e_col, t_col = st.columns(3)
        if 'Symbol' in df.columns and not df.empty:
            btc_df = df[df['Symbol']=='BTC']
            if not btc_df.empty:
                btc = btc_df.iloc[0]
                btc_price = btc.get('current_price', 0); btc_price = btc_price if pd.notnull(btc_price) else 0
                btc_change = btc.get('24h %', 0); btc_change = btc_change if pd.notnull(btc_change) else 0
                b_col.metric(f"BTC Price", f"{btc_price:,.2f} {currency.upper()}", f"{btc_change:.2f}%")
            else: b_col.metric(f"BTC Price", "N/A", "N/A")
            eth_df = df[df['Symbol']=='ETH']
            if not eth_df.empty:
                eth = eth_df.iloc[0]
                eth_price = eth.get('current_price', 0); eth_price = eth_price if pd.notnull(eth_price) else 0
                eth_change = eth.get('24h %', 0); eth_change = eth_change if pd.notnull(eth_change) else 0
                e_col.metric(f"ETH Price", f"{eth_price:,.2f} {currency.upper()}", f"{eth_change:.2f}%")
            else: e_col.metric(f"ETH Price", "N/A", "N/A")
        else:
            b_col.metric(f"BTC Price", "N/A", "Data Error"); e_col.metric(f"ETH Price", "N/A", "Data Error")

        if '24h %' in df.columns and not df.empty:
            df_numeric_24h = df.copy()
            df_numeric_24h['24h %'] = pd.to_numeric(df_numeric_24h['24h %'], errors='coerce')
            if not df_numeric_24h['24h %'].isna().all():
                try:
                    top24_idx = df_numeric_24h['24h %'].idxmax()
                    top24 = df.loc[top24_idx]  
                    top24_change = top24.get('24h %', 0.0); top24_change = top24_change if pd.notnull(top24_change) else 0.0
                    t_col.metric(f"Top 24h Gainer", f"{top24.get('name', 'N/A')}", f"{top24_change:.2f}%")
                except ValueError: # Handles cases like all NaNs after coerce
                    t_col.metric(f"Top 24h Gainer", "N/A", "Error")
            else:
                t_col.metric(f"Top 24h Gainer", "N/A", "No valid gainers")
        else:
            t_col.metric(f"Top 24h Gainer", "N/A", "Data unavailable")
        st.markdown("---")

        st.subheader(f"Top Movers ({timeframe})")
        col_map = {'24h':'24h %','7d':'7d %','30d':'30d %'}
        pc_col_name = col_map.get(timeframe, '24h %')
        if pc_col_name in df.columns and not df.empty and not df[pc_col_name].isna().all():
            df_copy_movers = df.copy()
            df_copy_movers[pc_col_name] = pd.to_numeric(df_copy_movers[pc_col_name], errors='coerce').fillna(0.0)
            g = df_copy_movers.sort_values(pc_col_name, ascending=False).head(10)
            l = df_copy_movers.sort_values(pc_col_name, ascending=True).head(10)
        else:
            g, l = pd.DataFrame(), pd.DataFrame()
            st.caption(f"Data for {timeframe} movers not available.")
        gc, lc = st.columns(2)
        with gc: display_market_movers(g, f"Gainers ({timeframe})", "🚀", pc_col_name)
        with lc: display_market_movers(l, f"Losers ({timeframe})", "📉", pc_col_name)
        st.markdown("---")

        st.subheader("Market Overview (Top 50 by Market Cap)")
        tbl_data_default = df.head(50)
        if tbl_data_default.empty and not df.empty : # If df has data but head(50) is somehow empty (should not happen with valid df)
            st.info("No data for Top 50, showing all available if any.")
            render_coins_table(df, currency)
        elif tbl_data_default.empty: # If df itself is empty, this was handled by main already
            st.info("No market data to display.")
        else:
            render_coins_table(tbl_data_default, currency)

# ================
# MAIN APP LOGIC
# ================
if df.empty:
    st.warning("Unable to load market data. Please check your internet connection, ensure the CoinGecko API is accessible, or try refreshing the page after a few moments.")
    if st.button("🔄 Try Refreshing Data", key="refresh_data_button_main"):
        st.cache_data.clear()  
        st.rerun()
else:
    if st.session_state.selected_coin_id:
        display_coin_details()
    else:
        display_market_overview()

# ========================
# PRICE ALERTS (in sidebar)
# ========================
with st.sidebar:
    st.header("🔔 Price Alerts")
    if not df.empty and 'id' in df.columns and 'name' in df.columns and 'current_price' in df.columns:
        # Using unique IDs for options, and mapping names for display
        alert_coin_options_dict = pd.Series(df.name.values, index=df.id).to_dict()
        # Filter out if name is NaN or empty after conversion to string
        alert_coin_options_dict = {k: str(v) for k, v in alert_coin_options_dict.items() if pd.notna(v) and str(v).strip()}


        if not alert_coin_options_dict:
            st.info("No coins available for setting alerts.")
        else:
            selected_coin_ids_for_alert = st.multiselect(
                'Monitor Coins',  
                options=list(alert_coin_options_dict.keys()),  
                format_func=lambda coin_id: alert_coin_options_dict.get(coin_id, str(coin_id)),
                key="alert_multiselect"
            )
            
            for coin_id_watched_alert in selected_coin_ids_for_alert:
                coin_data_series_list_alert = df[df['id'] == coin_id_watched_alert]
                if not coin_data_series_list_alert.empty:
                    cd_alert = coin_data_series_list_alert.iloc[0]
                    coin_name_watched_alert = str(cd_alert.get('name', coin_id_watched_alert))  
                    current_price_alert_val = cd_alert.get('current_price', 0.0)
                    current_price_alert_val = float(current_price_alert_val) if pd.notnull(current_price_alert_val) else 0.0

                    target_price_key_alert = f"alert_target_{coin_id_watched_alert}"  
                    
                    if target_price_key_alert not in st.session_state:
                        st.session_state[target_price_key_alert] = float(current_price_alert_val * 1.05) if current_price_alert_val > 0 else 0.01

                    widget_key_alert_input = f"user_alert_input_{coin_id_watched_alert}"
                    
                    user_target_price_alert = st.number_input(
                        f"Target for {coin_name_watched_alert} (now: {current_price_alert_val:,.4f} {currency.upper()})",
                        value=float(st.session_state[target_price_key_alert]),  
                        min_value=0.0,
                        format="%.6f",  
                        key=widget_key_alert_input  
                    )
                    
                    st.session_state[target_price_key_alert] = user_target_price_alert  
                    
                    alert_hit_key_name = f"alert_hit_{coin_id_watched_alert}_{user_target_price_alert}"
                    
                    if current_price_alert_val > 0 and user_target_price_alert > 0 and current_price_alert_val >= user_target_price_alert:
                        if not st.session_state.get(alert_hit_key_name, False):
                            st.success(f"🔔 ALERT! {coin_name_watched_alert} reached {user_target_price_alert:,.4f} {currency.upper()}!")
                            st.balloons()
                            st.session_state[alert_hit_key_name] = True  
                    elif st.session_state.get(alert_hit_key_name, False) and current_price_alert_val < user_target_price_alert:
                        st.session_state[alert_hit_key_name] = False # Reset if price drops
                # else: st.caption(f"Alert data for {coin_id_watched_alert} not found.") # Can be verbose
    else:
        st.info("Market data not fully loaded for alerts.")

# ========================
# AUTO-REFRESH LOGIC
# ========================
# Display last refresh time to user
st.sidebar.markdown(f"")
st.sidebar.caption(f"Last data refresh: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_refresh))}")

# Check and trigger refresh
if time.time() - st.session_state.get('last_refresh', 0) > refresh_interval:
    st.session_state.last_refresh = time.time()
    # st.cache_data.clear() # Uncomment this line if you want to clear *all* data caches on refresh
    st.rerun()
