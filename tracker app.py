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
.stTextInput > div > div > input {border-radius: 8px; border: 1px solid #4A4A4A;}
.stTextInput label {font-weight: bold; color: #E0E0E0;}
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

@st.cache_data(ttl=60)
def load_market_data(vs_currency: str):
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency, order='market_cap_desc', per_page=250,
            sparkline=True, price_change_percentage='24h,7d,30d'
        )
        if not data:
            # st.warning(f"No market data received from API for currency: {vs_currency}.") # Reduced verbosity
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

@st.cache_data(ttl=3600)
def get_ohlc_data(coin_id: str, vs_currency: str, days: int = 30):
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
    refresh_interval = st.slider('Refresh Interval (s)', 10, 300, 60, key="refresh_slider")

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
        # This function assumes the caller handles "no results" messages for search.
        # For default overview, if df itself is empty, it's handled before.
        # If data_df_to_render is empty (e.g. search yielded no results but df wasn't empty),
        # the caller should show an st.info message. This function will just show nothing.
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

    st.subheader(f"{coin_name_detail} ({coin_symbol_detail})")
    if st.button("⬅️ Back to Overview", key=f"back_button_{coin_id_detail}"): 
        st.session_state.selected_coin_id=None
        st.session_state.search_query = "" # Clear search when going back from detail
        st.rerun()

    chart_type = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"], key=f"chart_type_{coin_id_detail}")
    days = st.slider("History (days)", min_value=1, max_value=365, value=30, key=f"days_{coin_id_detail}")

    fig_data_loaded = False
    if chart_type == "Line":
        hist = get_historical_data(coin_id_detail, currency, days)
        if not hist.empty and 'price' in hist.columns and not hist['price'].isna().all():
            fig = px.line(hist, x='date', y='price', title=f"{coin_name_detail} Price (Last {days}d)",
                          labels={'price':f'Price ({currency.upper()})','date':'Date'})
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF", title_font_color="#FFFFFF")
            fig.update_xaxes(showgrid=False, color="#FFFFFF")
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#FFFFFF")
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
    else: 
        ohlc = get_ohlc_data(coin_id_detail, currency, days)
        if not ohlc.empty and all(col in ohlc.columns for col in ['open', 'high', 'low', 'close']):
            if chart_type == "Candlestick":
                fig = go.Figure(data=[
                    go.Candlestick(x=ohlc['date'], open=ohlc['open'], high=ohlc['high'], low=ohlc['low'], close=ohlc['close'])
                ])
            else: # OHLC
                fig = go.Figure(data=[
                    go.Ohlc(x=ohlc['date'], open=ohlc['open'], high=ohlc['high'], low=ohlc['low'], close=ohlc['close'])
                ])
            fig.update_layout(title=f"{coin_name_detail} {chart_type} Chart (Last {days}d)",
                              xaxis_rangeslider_visible=False,
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF", title_font_color="#FFFFFF")
            fig.update_xaxes(showgrid=False, color="#FFFFFF")
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#FFFFFF")
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
    
    if not fig_data_loaded:
        st.info(f"No chart data to display for {coin_name_detail} for the selected period or type.")

    st.subheader("Info & Metrics")
    c1_detail, c2_detail = st.columns(2)
    
    current_price_val = coin.get('current_price', 0.0); current_price_val = current_price_val if pd.notnull(current_price_val) else 0.0
    change_24h_val = coin.get('24h %', 0.0); change_24h_val = change_24h_val if pd.notnull(change_24h_val) else 0.0
    market_cap_val = coin.get('market_cap', 0); market_cap_val = market_cap_val if pd.notnull(market_cap_val) else 0
    total_volume_val = coin.get('total_volume', 0); total_volume_val = total_volume_val if pd.notnull(total_volume_val) else 0
    
    c1_detail.metric("Price", f"{current_price_val:,.4f} {currency.upper()}", f"{change_24h_val:.2f}%")
    c2_detail.metric("Market Cap", f"${market_cap_val:,}" if currency.lower() == 'usd' else f"{market_cap_val:,} {currency.upper()}")
    c1_detail.metric("24h Vol", f"${total_volume_val:,}" if currency.lower() == 'usd' else f"{total_volume_val:,} {currency.upper()}")
    c2_detail.metric("Rank", f"#{coin.get('market_cap_rank', 'N/A')}")

# ========================
# MARKET OVERVIEW (Main Display Logic with Search)
# ========================
def display_market_overview():
    # Search Bar
    search_cols_c1, search_cols_c2, search_cols_c3 = st.columns([0.5, 2, 0.5]) # Centering the search bar a bit
    with search_cols_c2:
        search_query_input = st.text_input(
            "🔍 Search Coins (by Name or Symbol)",
            value=st.session_state.get("search_query", ""),
            placeholder="E.g., Bitcoin or BTC",
            key="search_bar_input_main_page" # Ensure unique key
        )

    if search_query_input != st.session_state.get("search_query", ""):
        st.session_state.search_query = search_query_input
        st.rerun()

    search_active = bool(st.session_state.get("search_query", "").strip())

    if search_active:
        st.markdown("---") 
        
        back_button_cols_c1, back_button_cols_c2 = st.columns([1, 4])
        with back_button_cols_c1:
            if st.button("⬅️ Clear Search", key="clear_search_button_active"):
                st.session_state.search_query = ""
                st.rerun()
        with back_button_cols_c2:
            st.subheader(f"Search Results for \"{st.session_state.search_query}\"")
        
        query = st.session_state.search_query.lower()
        
        # Ensure df is not empty before attempting to search
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
            # ... (rest of Key Metrics logic as in previous versions)
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
if time.time() - st.session_state.get('last_refresh', 0) > refresh_interval:
    st.session_state.last_refresh = time.time()
    # st.cache_data.clear() # Optional: uncomment if you want full data refresh on interval
    st.rerun()
