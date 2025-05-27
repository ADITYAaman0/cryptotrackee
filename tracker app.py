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
/* Base body style for font and color */
body {
    font-family: 'Arial', sans-serif; /* Common, clean font */
    color: #EAEAEA; /* Light gray for general text */
}

.central-header {
    font-size:3.2rem; /* Slightly reduced for better balance */
    font-weight:bold;
    text-align:center;
    color:#4CAF50; /* Theme green */
    margin-bottom:20px;
    text-shadow: 1px 1px 2px #111;
}
.stMetric {
    background:#2E2E38; /* Darker, slightly purple-ish gray */
    border-radius:12px;
    padding:15px; /* Adjusted padding */
    border:1px solid #555;
}
.stMetricLabel {
    color: #A0A0A0; /* Lighter label for metrics */
    font-size: 0.95rem;
    font-weight: 500;
}
.stMetricValue {
    font-size: 1.6rem; /* Slightly larger */
    color: #FFFFFF;
    font-weight: 600;
}
.mover-header {
    font-size:1.6rem;
    font-weight:bold;
    color:#66BB6A; /* Lighter green */
    padding-bottom:10px;
    border-bottom:2px solid #66BB6A;
}
.mover-row {display:flex; align-items:center; margin-bottom:10px;}
.mover-name {font-weight:bold; margin-left:10px; color: #D0D0D0;}

/* Attractive Search Bar Styling */
.stTextInput > div > div > input {
    border-radius: 25px;
    border: 2px solid #4CAF50;
    padding: 10px 15px;
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    transition: 0.3s;
    color: #E0E0E0;
    background-color: #1A1A1A;
}
.stTextInput > div > div > input:focus {
    border-color: #2196F3;
    box-shadow: 0 4px 12px 0 rgba(33,150,243,0.3);
}
.stTextInput label {
    font-weight: bold;
    color: #E0E0E0;
    font-size: 1.1rem;
    margin-bottom: 5px;
    display: block;
}
/* Style for the "Clear Search" and "Back" buttons */
.stButton > button {
    border-radius: 8px;
    border: 1px solid #03A9F4; /* Light Blue border */
    background-color: transparent; /* Transparent background */
    color: #03A9F4; /* Light Blue text */
    padding: 8px 15px;
    font-weight: bold;
    transition: 0.2s;
}
.stButton > button:hover {
    background-color: #03A9F4; /* Light Blue on hover */
    color: white;
    border-color: #03A9F4;
}
.stButton > button:active { /* Style for when button is clicked */
    background-color: #0277BD !important;
    color: white !important;
}
/* Custom styling for chart info metrics */
.chart-info-metric {
    font-size: 1rem; /* Adjusted size */
    color: #C0C0C0; /* Lighter grey */
    margin-right: 12px; /* Adjusted spacing */
    display: inline-block;
}
.chart-info-value {
    font-weight: bold;
    color: #FFFFFF; /* White value */
}
.change-positive { color: #4CAF50; }
.change-negative { color: #F44336; }

/* Table specific font styles */
.table-header-text { font-weight: bold; color: #B0BEC5; font-size: 0.9rem; } /* Lighter, slightly smaller */
.table-coin-name { font-weight: 500; color: #CFD8DC; } /* Readable coin name */
.table-coin-name-clickable { cursor: pointer; transition: color 0.2s; }
.table-coin-name-clickable:hover { color: #4CAF50; } /* Highlight on hover */
.table-price { color: #ECEFF1; font-weight: 500; }
.table-mkt-cap { color: #90A4AE; font-size:0.85rem; } /* Softer color for mkt cap */

/* Watchlist Buttons Styling */
.watchlist-button button {
    background-color: transparent;
    border: 1px solid #4CAF50;
    color: #4CAF50;
    padding: 2px 6px !important; /* Smaller padding */
    font-size: 0.9rem !important; /* Smaller font */
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.2s, color 0.2s;
    line-height: 1.2; /* Ensure text fits */
    min-width: 30px; /* Ensure button has some width for icon */
    text-align: center;
}
.watchlist-button.remove button {
    border-color: #F44336;
    color: #F44336;
}
.watchlist-button button:hover {
    background-color: #4CAF50;
    color: white;
}
.watchlist-button.remove button:hover {
    background-color: #F44336;
    color: white;
}

.watchlist-empty-message {
    text-align:center;
    font-style:italic;
    color:#78909C; /* Bluish grey */
    margin-top:25px;
    font-size:1.25rem;
}
.section-subheader { /* For Watchlist title and Search Results */
    font-size:1.8rem;
    font-weight:bold;
    color:#4CAF50;
    margin-top:20px;
    margin-bottom:15px;
    border-bottom: 2px solid #4CAF50;
    padding-bottom:5px;
}
/* Font for coin name in detail view */
.detail-coin-name { font-size: 2.2rem; font-weight: bold; color: #FFFFFF; }
.detail-coin-symbol { font-size: 1.3rem; color: #B0BEC5; margin-left: 10px; }

/* Chart control labels */
.stRadio label, .stSelectbox label { /* Target Streamlit's generated classes carefully */
    color: #B0BEC5 !important;
    font-weight: 500 !important;
    font-size: 1rem !important;
}
/* Styling the tab headers for better visibility */
.stTabs [data-baseweb="tab-list"] {
    gap: 18px; /* Spacing between tabs */
    background-color: #1A1A1A;
    padding: 8px;
    border-radius: 8px;
    border-bottom: 2px solid #333; /* Separator for tab list */
}
.stTabs [data-baseweb="tab"] {
    height: 42px;
    white-space: pre-wrap;
    background-color: #262730;
    border-radius: 6px;
    color: #A0A0A0;
    font-weight: 500;
    font-size: 0.95rem; /* Tab font size */
    padding-left: 15px;
    padding-right: 15px;
    transition: background-color 0.3s, color 0.3s;
}
.stTabs [aria-selected="true"] {
    background-color: #4CAF50;
    color: white !important;
    font-weight: bold;
}
.stButton.watchlist-detail-button button { /* Specific class for watchlist button in detail view */
    border: 1px solid #FF9800; /* Orange for visibility */
    color: #FF9800;
    background-color: transparent;
}
.stButton.watchlist-detail-button button:hover {
    background-color: #FF9800;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# Header animation
with st.container():
    col1_header, col2_header, col3_header = st.columns([1,3,1])
    with col2_header:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim: st_lottie(anim, height=180, key="header_animation") # Slightly smaller animation
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
        buf = BytesIO(); fig.write_image(buf, format='png', engine='kaleido') # engine='kaleido' might need kaleido installed
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    except Exception: # Broad exception for robustness in sparkline generation
        return ""

@st.cache_data(ttl=30)
def load_market_data(vs_currency: str):
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency, order='market_cap_desc', per_page=250,
            sparkline=True, price_change_percentage='24h,7d,30d'
        )
        if not data: return pd.DataFrame()
        df_loaded = pd.DataFrame(data)
        if df_loaded.empty: return pd.DataFrame()

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
    ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
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
            supported = ['usd']; cur_idx = 0
            st.warning("Could not fetch supported currencies. Using USD.")
    except Exception:
        supported = ['usd']; cur_idx = 0
        st.warning(f"Could not fetch supported currencies. Using USD.")
        
    currency = st.selectbox('Currency', supported, index=cur_idx, key="currency_select")
    timeframe = st.selectbox('Movers Timeframe', ['24h','7d','30d'], index=1, key="timeframe_select")  
    refresh_interval = st.slider('Auto-Refresh Interval (s)', 10, 300, 30, key="refresh_slider")

# ========================
# SESSION STATE INITIALIZATION
# ========================
if 'selected_coin_id' not in st.session_state: st.session_state.selected_coin_id = None
if 'last_refresh' not in st.session_state: st.session_state.last_refresh = time.time()
if 'search_query' not in st.session_state: st.session_state.search_query = ""
if 'watchlist' not in st.session_state: st.session_state.watchlist = [] # List of coin IDs

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
        ch = r_mov.get(pct_col_name, 0.0); ch = ch if pd.notnull(ch) else 0.0
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

    # Adjusted column spec for Watchlist button
    header_cols_spec = [0.3, 2.0, 1.3, 0.7, 1.5, 1.2, 0.5] 
    header_cols = st.columns(header_cols_spec)
    headers = ["#", "Coin", f"Price ({currency_symbol_for_table.upper()})", "24h %", "Market Cap", "7d Sparkline", "❤️"]
    
    for col, header_text in zip(header_cols, headers):
        col.markdown(f"<span class='table-header-text'>{header_text}</span>", unsafe_allow_html=True)

    for index, r_row_table in data_df_to_render.iterrows():
        row_cols = st.columns(header_cols_spec)  
        
        if not isinstance(r_row_table, pd.Series): continue

        row_cols[0].markdown(f"<span style='font-size:0.85rem; color: #B0BEC5;'>{r_row_table.get('market_cap_rank', 'N/A')}</span>", unsafe_allow_html=True)
        
        coin_id_tbl_render = str(r_row_table.get('id', f"unknown_TABLE_{index}"))
        coin_name_tbl_render = str(r_row_table.get('name', 'N/A'))
        coin_symbol_tbl_render = str(r_row_table.get('Symbol', 'N/A'))
        
        coin_label_render = f"{coin_name_tbl_render} ({coin_symbol_tbl_render})"
        logo_url_render = r_row_table.get('Logo', '')

        # Coin Name (clickable)
        # Using st.button for clickability and Python callback directly
        button_container = row_cols[1].empty() # Create a container for the button
        
        # To make the text look like a link, we use markdown within a container that hosts a button
        # This is a common pattern: display rich text, make it clickable with an st.button
        
        # Define the clickable coin name display
        coin_display_html = f"""
        <div style='display:flex; align-items:center;' class='table-coin-name-clickable'>
            {f"<img src='{logo_url_render}' width='24' height='24' style='margin-right:8px; vertical-align:middle;'>" if logo_url_render else "<span style='width:32px; display:inline-block;'></span>"}
            <span class='table-coin-name'>{coin_label_render}</span>
        </div>
        """
        row_cols[1].markdown(coin_display_html, unsafe_allow_html=True)
        
        # Add an invisible button over it or a small clickable icon for navigation
        # For simplicity, making the whole cell clickable for navigation using a transparent button
        # This will overlay the markdown. A bit hacky.
        # A better way is to have a specific "details" button or just rely on users knowing to click.
        # Or, use a callback on the entire row if Streamlit evolves to support it easily.
        # For now, let's make a small, explicit select button or rely on watchlist navigation.
        # To avoid complexity of overlapping, we'll keep the original hidden button logic slightly modified.
        
        # Simplified: Use a transparent button for the action, markdown for display
        if row_cols[1].button(" ", key=f"select_COIN_{coin_id_tbl_render}_{index}", help=f"View details for {coin_name_tbl_render}", use_container_width=True):
            st.session_state.selected_coin_id = coin_id_tbl_render  
            st.session_state.search_query = "" 
            st.rerun()
        # The above button will be nearly invisible. The text is shown by markdown.


        current_price_val_row_render = r_row_table.get('current_price', 0.0); current_price_val_row_render = current_price_val_row_render if pd.notnull(current_price_val_row_render) else 0.0
        row_cols[2].markdown(f"<span class='table-price'>{current_price_val_row_render:,.4f}</span>", unsafe_allow_html=True)
        
        change_24h_tbl_render = r_row_table.get('24h %', 0.0); change_24h_tbl_render = change_24h_tbl_render if pd.notnull(change_24h_tbl_render) else 0.0
        clr_tbl_render = 'change-positive' if change_24h_tbl_render >= 0 else 'change-negative'
        row_cols[3].markdown(f"<div class='{clr_tbl_render}' style='font-weight:bold; text-align:left;'>{change_24h_tbl_render:+.2f}%</div>", unsafe_allow_html=True)
        
        market_cap_val_row_render = r_row_table.get('market_cap', 0); market_cap_val_row_render = market_cap_val_row_render if pd.notnull(market_cap_val_row_render) else 0
        row_cols[4].markdown(f"<span class='table-mkt-cap'>${market_cap_val_row_render:,}</span>" if currency_symbol_for_table.lower() == 'usd' else f"<span class='table-mkt-cap'>{market_cap_val_row_render:,} {currency_symbol_for_table.upper()}</span>", unsafe_allow_html=True)
        
        sparkline_html_render = r_row_table.get('7d Sparkline', '')
        if sparkline_html_render:
            row_cols[5].markdown(f"<img src='{sparkline_html_render}' alt='7d sparkline for {coin_name_tbl_render}'>", unsafe_allow_html=True)
        else:
            row_cols[5].caption("N/A")

        # Watchlist Toggle Button
        is_in_watchlist = coin_id_tbl_render in st.session_state.watchlist
        button_symbol = "➖" if is_in_watchlist else "➕"
        button_help = "Remove from Watchlist" if is_in_watchlist else "Add to Watchlist"
        button_class = "remove" if is_in_watchlist else "add"
        
        # Use a container for the button to apply specific class for styling
        button_container = row_cols[6].empty() 
        with button_container.container():
            st.markdown(f"<div class='watchlist-button {button_class}'>", unsafe_allow_html=True) # Apply class to div
            if st.button(button_symbol, key=f"watch_TABLE_{coin_id_tbl_render}_{index}", help=button_help):
                if is_in_watchlist:
                    st.session_state.watchlist.remove(coin_id_tbl_render)
                    st.toast(f"{coin_name_tbl_render} removed from watchlist!", icon="💔")
                else:
                    st.session_state.watchlist.append(coin_id_tbl_render)
                    st.toast(f"{coin_name_tbl_render} added to watchlist!", icon="💖")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin-top:0.3rem; margin-bottom:0.3rem; border-top: 1px solid #333;'>", unsafe_allow_html=True)

# ========================
# WATCHLIST TAB DISPLAY
# ========================
def display_watchlist_tab(main_df, currency_symbol):
    st.markdown("<p class='section-subheader'>⭐ My Watchlist</p>", unsafe_allow_html=True)
    
    if not st.session_state.watchlist:
        st.markdown("<p class='watchlist-empty-message'>Your watchlist is empty. Add coins from the Market Overview or search results!</p>", unsafe_allow_html=True)
        # Lottie animation for empty watchlist
        empty_watch_anim = load_lottie("https://lottie.host/9c4a4279-3525-4749-942e-39a539476f32/HjYBA1z1U3.json") # Example: sad face or empty box
        if empty_watch_anim:
             st_lottie(empty_watch_anim, height=200, key="empty_watchlist_anim")
        return

    watchlist_df = main_df[main_df['id'].isin(st.session_state.watchlist)]

    if watchlist_df.empty: # Handles if watched coins are no longer in main_df (e.g. API changes, delisting)
        st.markdown("<p class='watchlist-empty-message'>Could not load data for your watched coins. They might be delisted or data is temporarily unavailable.</p>", unsafe_allow_html=True)
        st.caption("The following coin IDs were in your watchlist but not found:")
        for coin_id_missing in st.session_state.watchlist:
            if coin_id_missing not in main_df['id'].tolist():
                 st.caption(f"- {coin_id_missing}")
        return
    
    render_coins_table(watchlist_df, currency_symbol)


# ========================
# DETAIL VIEW
# ========================
def display_coin_details():
    selected_id = st.session_state.selected_coin_id
    if selected_id is None or 'id' not in df.columns:
        st.warning("Coin data or selection is invalid. Returning to overview.")
        st.session_state.selected_coin_id = None; st.rerun()
        return

    sel = df[df['id'] == selected_id]
    if sel.empty:
        st.warning(f"Selected coin (ID: {selected_id}) not found. Returning to overview.")
        st.session_state.selected_coin_id = None; st.rerun()
        return  
        
    coin = sel.iloc[0]
    coin_name_detail = coin.get('name', 'N/A')
    coin_symbol_detail = coin.get('Symbol', 'N/A')
    coin_id_detail = coin.get('id', 'unknown')
    coin_logo_detail = coin.get('Logo', '')

    # Top bar: Logo, Name, Symbol, Watchlist Button, Back Button
    top_bar_cols = st.columns([0.08, 0.5, 0.2, 0.22]) # Adjust ratios as needed
    with top_bar_cols[0]:
        if coin_logo_detail: st.image(coin_logo_detail, width=50)
    with top_bar_cols[1]:
        st.markdown(f"<span class='detail-coin-name'>{coin_name_detail}</span> <span class='detail-coin-symbol'>{coin_symbol_detail.upper()}</span>", unsafe_allow_html=True)
    
    with top_bar_cols[2]: # Watchlist button
        is_in_watchlist_detail = coin_id_detail in st.session_state.watchlist
        watch_button_text = "💔 Remove" if is_in_watchlist_detail else "💖 Add to Watchlist"
        watch_button_key = f"watch_DETAIL_{coin_id_detail}"
        # Apply a specific class for this button if different styling is needed
        st.markdown("<div class='stButton watchlist-detail-button'>", unsafe_allow_html=True) # Wrapper for specific CSS
        if st.button(watch_button_text, key=watch_button_key, help="Toggle Watchlist Status"):
            if is_in_watchlist_detail:
                st.session_state.watchlist.remove(coin_id_detail)
                st.toast(f"{coin_name_detail} removed from watchlist!", icon="💔")
            else:
                st.session_state.watchlist.append(coin_id_detail)
                st.toast(f"{coin_name_detail} added to watchlist!", icon="💖")
            # No rerun here, allow current view to update if button text changes, or rerun if state needs wide refresh
            st.experimental_rerun() # Rerun to update button text and potentially other dependent states
        st.markdown("</div>", unsafe_allow_html=True)


    with top_bar_cols[3]: # Back button
        if st.button("⬅️ Back to Overview", key=f"back_button_{coin_id_detail}"):  
            st.session_state.selected_coin_id=None
            st.session_state.search_query = ""
            st.rerun()
    st.markdown("---")

    # Price Metrics Bar (below Name/Symbol)
    metric_cols = st.columns([1,1,0.5,0.5,0.5,0.5]) # Price, 24h%, O, H, L, C
    ohlc_for_metrics = get_raw_ohlc_data_from_coingecko(coin_id_detail, currency, days=1)  
    latest_price_info = ohlc_for_metrics.iloc[-1] if not ohlc_for_metrics.empty else {}
    
    current_price_val = coin.get('current_price', 0.0)
    change_24h_val = coin.get('24h %', 0.0)
    change_color_class = "change-positive" if change_24h_val >= 0 else "change-negative"

    metric_cols[0].markdown(f"<span class='chart-info-metric'>Price: <span class='chart-info-value'>{current_price_val:,.4f} {currency.upper()}</span></span>", unsafe_allow_html=True)
    metric_cols[1].markdown(f"<span class='chart-info-metric'>24h Change: <span class='chart-info-value {change_color_class}'>{change_24h_val:+.2f}%</span></span>", unsafe_allow_html=True)

    if not ohlc_for_metrics.empty:
        metric_cols[2].markdown(f"<span class='chart-info-metric'>O: <span class='chart-info-value'>{latest_price_info.get('open',0.0):,.4f}</span></span>", unsafe_allow_html=True)
        metric_cols[3].markdown(f"<span class='chart-info-metric'>H: <span class='chart-info-value'>{latest_price_info.get('high',0.0):,.4f}</span></span>", unsafe_allow_html=True)
        metric_cols[4].markdown(f"<span class='chart-info-metric'>L: <span class='chart-info-value'>{latest_price_info.get('low',0.0):,.4f}</span></span>", unsafe_allow_html=True)
        metric_cols[5].markdown(f"<span class='chart-info-metric'>C: <span class='chart-info-value'>{latest_price_info.get('close',0.0):,.4f}</span></span>", unsafe_allow_html=True)
    st.markdown("---") 

    # Chart Controls (Timeframe and Type)
    chart_controls_cols = st.columns([3, 1]) 
    with chart_controls_cols[0]:
        timeframe_options = ['1m', '5m', '10m', '15m', '30m', '1h', '4h', '1D', '7D', '1M', '3M', '6M', '1Y', 'MAX']
        default_timeframe_index = timeframe_options.index('1D') if '1D' in timeframe_options else 7 # fallback if '1D' removed
        selected_timeframe = st.radio(
            "Select Timeframe:", options=timeframe_options, index=default_timeframe_index,
            horizontal=True, key=f"chart_timeframe_{coin_id_detail}"
        )
    with chart_controls_cols[1]:
        chart_type = st.selectbox("Chart Type:", ["Candlestick","Line","OHLC"], index=0, key=f"chart_type_{coin_id_detail}")

    # Chart rendering logic (remains largely the same as provided, with style updates)
    fig_data_loaded = False
    ohlc_data_for_chart = pd.DataFrame()
    line_data_for_chart = pd.DataFrame()

    coingecko_days_map_ohlc = {
        '1D': 1, '7D': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 365, 'MAX': 'max' # use string 'max' for historical
    }
    # For historical line chart, if MAX is chosen, Coingecko API accepts 'max'
    coingecko_days_map_hist = {**coingecko_days_map_ohlc, 'MAX': 'max'}


    if selected_timeframe in ['1m', '5m', '10m', '15m', '30m', '1h', '4h', '1D']:
        raw_1min_ohlc = get_raw_ohlc_data_from_coingecko(coin_id_detail, currency, days=1) # 'days=1' gives minute data
        if not raw_1min_ohlc.empty:
            if selected_timeframe == '1m' or selected_timeframe == '1D': # 1D on chart means 1-min candles for 24h
                ohlc_data_for_chart = raw_1min_ohlc
            else: 
                interval_map_pandas = {'5m': '5T', '10m': '10T', '15m': '15T', '30m': '30T', '1h': '1H', '4h': '4H'} # T for minutes
                resampling_interval = interval_map_pandas.get(selected_timeframe)
                if resampling_interval:
                    ohlc_data_for_chart = resample_ohlc_data(raw_1min_ohlc, resampling_interval)
        # If ohlc_data_for_chart is still empty, appropriate message will be shown later
            
    elif selected_timeframe in ['7D', '1M', '3M', '6M', '1Y', 'MAX']:
        days_param_ohlc = coingecko_days_map_ohlc.get(selected_timeframe)
        if days_param_ohlc: # 'max' is not for OHLC endpoint in this way
             ohlc_data_for_chart = get_raw_ohlc_data_from_coingecko(coin_id_detail, currency, days=days_param_ohlc if days_param_ohlc != 'max' else 365*2) # Cap 'max' for OHLC to avoid too much data
    
    # Plotting
    chart_title_text = f"{coin_name_detail} - {chart_type} ({selected_timeframe} Intervals)"
    common_layout_updates = dict(
        title={'text': chart_title_text, 'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'color': '#FFFFFF', 'size': 16}},
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(20,20,25,0.5)', # Slightly visible plot background
        font_color="#E0E0E0",
        xaxis=dict(showgrid=True, color="#B0BEC5", linecolor="#444", gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#B0BEC5", linecolor="#444", side='right'),
        hovermode="x unified",
        legend=dict(font=dict(color="#E0E0E0"))
    )

    if chart_type in ["Candlestick", "OHLC"]:
        if not ohlc_data_for_chart.empty and all(col in ohlc_data_for_chart.columns for col in ['open', 'high', 'low', 'close']):
            fig_class = go.Candlestick if chart_type == "Candlestick" else go.Ohlc
            fig = go.Figure(data=[
                fig_class(
                    x=ohlc_data_for_chart['date'], open=ohlc_data_for_chart['open'], high=ohlc_data_for_chart['high'],
                    low=ohlc_data_for_chart['low'], close=ohlc_data_for_chart['close'],
                    increasing_line_color='#4CAF50', decreasing_line_color='#F44336'
                )
            ])
            fig.update_layout(xaxis_rangeslider_visible=False, **common_layout_updates)
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
        else:
            st.info(f"No OHLC data for {chart_type} chart for {coin_name_detail} at '{selected_timeframe}' interval.")
    elif chart_type == "Line":
        hist_days_param = coingecko_days_map_hist.get(selected_timeframe, 1 if selected_timeframe not in ['1m','5m','10m','15m','30m','1h','4h'] else 1)
        if selected_timeframe in ['1m','5m','10m','15m','30m','1h','4h']: # For these, use 1-day data for finer granularity
            hist_days_param = 1
        
        line_data_for_chart = get_historical_data(coin_id_detail, currency, days=hist_days_param)
        
        if not line_data_for_chart.empty and 'price' in line_data_for_chart.columns and not line_data_for_chart['price'].isna().all():
            fig = px.line(line_data_for_chart, x='date', y='price',
                          labels={'price':f'Price ({currency.upper()})','date':'Date'})
            fig.update_traces(line=dict(color='#2196F3', width=2)) # Blue line color
            fig.update_layout(**common_layout_updates)
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
        else:
            st.info(f"No data for Line chart for {coin_name_detail} at '{selected_timeframe}' interval.")
            
    if not fig_data_loaded:
        st.info(f"Chart data for {coin_name_detail} ({selected_timeframe}, {chart_type}) is currently unavailable or insufficient.")

    st.markdown("---")
    st.subheader("Info & Metrics")
    c1_detail, c2_detail, c3_detail = st.columns(3) # Added one more column for Rank
    market_cap_val = coin.get('market_cap', 0); market_cap_val = market_cap_val if pd.notnull(market_cap_val) else 0
    total_volume_val = coin.get('total_volume', 0); total_volume_val = total_volume_val if pd.notnull(total_volume_val) else 0
    
    c1_detail.metric("Market Cap", f"${market_cap_val:,}" if currency.lower() == 'usd' else f"{market_cap_val:,} {currency.upper()}")
    c2_detail.metric("24h Volume", f"${total_volume_val:,}" if currency.lower() == 'usd' else f"{total_volume_val:,} {currency.upper()}")
    c3_detail.metric("Market Cap Rank", f"#{coin.get('market_cap_rank', 'N/A')}")


# ========================
# MARKET OVERVIEW (Main Display Logic with Search)
# ========================
def display_market_overview():
    search_query_input = st.text_input(
        "🔍 Search Coins (by Name or Symbol)",
        value=st.session_state.get("search_query", ""),
        placeholder="E.g., Bitcoin or BTC",
        key="search_bar_input_main_page"
    )

    if search_query_input != st.session_state.get("search_query", ""):
        st.session_state.search_query = search_query_input
        st.rerun() # Rerun to reflect search results immediately

    search_active = bool(st.session_state.get("search_query", "").strip())

    if search_active:
        st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem; border-top: 1px solid #444;'>", unsafe_allow_html=True)
        
        col_search_title, col_clear_button = st.columns([0.8, 0.2])
        with col_search_title:
            st.markdown(f"<p class='section-subheader'>Search Results for \"{st.session_state.search_query}\"</p>", unsafe_allow_html=True)
        with col_clear_button:
            if st.button("🧹 Clear Search", key="clear_search_button_active", help="Clear search and show all coins"):
                st.session_state.search_query = ""
                st.rerun()
        
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
            st.caption(f"Found **{len(search_results_df)}** matching coin(s).")
            render_coins_table(search_results_df, currency)  
    else: # Default view (no active search)
        st.subheader("Key Metrics")
        b_col, e_col, t_col = st.columns(3) # Using 3 for key metrics (BTC, ETH, Total Market Cap if available)
        if 'Symbol' in df.columns and not df.empty:
            btc_df = df[df['Symbol']=='BTC']
            if not btc_df.empty:
                btc = btc_df.iloc[0]
                btc_price = btc.get('current_price', 0); btc_price = btc_price if pd.notnull(btc_price) else 0
                btc_change = btc.get('24h %', 0); btc_change = btc_change if pd.notnull(btc_change) else 0
                b_col.metric(f"BTC Price ({currency.upper()})", f"{btc_price:,.2f}", f"{btc_change:.2f}%")
            else: b_col.metric(f"BTC Price", "N/A", "N/A")
            
            eth_df = df[df['Symbol']=='ETH']
            if not eth_df.empty:
                eth = eth_df.iloc[0]
                eth_price = eth.get('current_price', 0); eth_price = eth_price if pd.notnull(eth_price) else 0
                eth_change = eth.get('24h %', 0); eth_change = eth_change if pd.notnull(eth_change) else 0
                e_col.metric(f"ETH Price ({currency.upper()})", f"{eth_price:,.2f}", f"{eth_change:.2f}%")
            else: e_col.metric(f"ETH Price", "N/A", "N/A")

            # Example: Total Market Cap metric (if available or meaningful from top coins)
            if 'market_cap' in df.columns and df['market_cap'].sum() > 0 :
                 total_mkt_cap_sum = df['market_cap'].sum()
                 t_col.metric(f"Total Mkt Cap (Top 250, {currency.upper()})", f"${total_mkt_cap_sum:,.0f}" if currency.lower()=='usd' else f"{total_mkt_cap_sum:,.0f}")
            else:
                 t_col.metric("Total Mkt Cap", "N/A")

        st.markdown("---")
        gainer_col, loser_col = st.columns(2)
        if not df.empty and timeframe + ' %' in df.columns: # Make sure the column for sorting exists
            pct_change_col = timeframe + ' %'
            df_sorted_gainers = df.sort_values(by=pct_change_col, ascending=False).head(5)
            df_sorted_losers = df.sort_values(by=pct_col_name, ascending=True).head(5) if pct_col_name in df.columns else pd.DataFrame()

            with gainer_col:
                display_market_movers(df_sorted_gainers, f"Top Gainers ({timeframe})", "🚀", pct_change_col)
            with loser_col:
                display_market_movers(df_sorted_losers, f"Top Losers ({timeframe})", "📉", pct_change_col)
        else:
            st.info(f"Market mover data for timeframe '{timeframe}' is not available.")
            
        st.markdown("---")
        st.subheader("All Coins (Top 250 by Market Cap)")
        render_coins_table(df.head(100), currency) # Displaying top 100 by default, or all of 'df'

# ========================
# MAIN APP LAYOUT (Using Tabs)
# ========================

# Auto-refresh logic
if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()


if st.session_state.selected_coin_id:
    display_coin_details() 
else:
    # Dynamic tab title for watchlist
    watchlist_count = len(st.session_state.watchlist)
    tab_titles = ["📊 Market Overview", f"⭐ Watchlist ({watchlist_count})"]
    
    tab1, tab2 = st.tabs(tab_titles)

    with tab1:
        display_market_overview()
    with tab2:
        if df.empty and watchlist_count > 0: # If df is empty but watchlist has items
            st.warning("Market data is currently unavailable. Cannot display full watchlist details. Please try refreshing.")
            st.markdown("<p class='section-subheader'>⭐ My Watched Coin IDs</p>", unsafe_allow_html=True)
            if not st.session_state.watchlist:
                 st.markdown("<p class='watchlist-empty-message'>Your watchlist is empty.</p>", unsafe_allow_html=True)
            else:
                for coin_id in st.session_state.watchlist:
                    st.markdown(f"- {coin_id} (Details unavailable without market data)")
        elif df.empty and watchlist_count == 0:
            display_watchlist_tab(df, currency) # Will show empty message
        else: # df is available
            display_watchlist_tab(df, currency)

st.sidebar.markdown("---")
st.sidebar.caption(f"Last refresh: {time.strftime('%H:%M:%S')}")
st.sidebar.caption(f"Data from CoinGecko API.")
