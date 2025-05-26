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
    except requests.exceptions.RequestException as e:
        # st.error(f"Failed to load Lottie animation: {e}") # Optional: show error to user
        return None

st.markdown("""
<style>
.central-header {font-size:3rem; font-weight:bold; text-align:center; color:#FFF; margin-bottom:20px;}
.stMetric {background:#262730; border-radius:12px; padding:20px; border:1px solid #4CAF50;}
.mover-header {font-size:1.5rem; font-weight:bold; color:#FFF; padding-bottom:10px; border-bottom:2px solid #4CAF50;}
.mover-row {display:flex; align-items:center; margin-bottom:10px;}
.mover-name {font-weight:bold; margin-left:10px;}
/* Ensure images in movers and table don't break layout if URL is broken */
.mover-row img, .stDataFrame img { object-fit: contain; }
</style>
""", unsafe_allow_html=True)

# Header animation
with st.container():
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
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

# sparkline generator
def create_sparkline(data):
    if not data or not isinstance(data, list) or len(data)<2: return ""
    try:
        # Ensure all data points are numeric, coercing errors to NaN then dropping
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
        buf = BytesIO(); fig.write_image(buf, format='png', engine='kaleido') # Ensure kaleido is installed
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    except Exception: # Catch error if kaleido is not available or image generation fails
        # st.warning("Sparkline generation failed. Ensure Kaleido is installed or data is valid.") # Optional warning
        return ""


@st.cache_data(ttl=60)
def load_market_data(vs_currency: str):
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency, order='market_cap_desc', per_page=250,
            sparkline=True, price_change_percentage='24h,7d,30d'
        )
        if not data:
            st.warning(f"No market data received from API for currency: {vs_currency}. This might be a temporary API issue.")
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame()

        # Safely create new columns with fallbacks
        df['24h %'] = pd.to_numeric(df.get('price_change_percentage_24h_in_currency'), errors='coerce').fillna(0.0)
        df['7d %']  = pd.to_numeric(df.get('price_change_percentage_7d_in_currency'), errors='coerce').fillna(0.0)
        df['30d %'] = pd.to_numeric(df.get('price_change_percentage_30d_in_currency'), errors='coerce').fillna(0.0)
        df['Symbol'] = df.get('symbol', pd.Series(dtype='object')).astype(str).str.upper().fillna('N/A')
        df['Logo']   = df.get('image', pd.Series(dtype='object')).astype(str).fillna('')
        df['id']     = df.get('id', pd.Series(dtype='object')).astype(str).fillna('unknown') # Ensure ID is string
        df['name']   = df.get('name', pd.Series(dtype='object')).astype(str).fillna('Unknown Coin')


        if 'sparkline_in_7d' in df.columns:
            df['7d Sparkline'] = df['sparkline_in_7d'].apply(
                lambda x: create_sparkline(x.get('price', [])) if isinstance(x, dict) and x.get('price') else ""
            )
        else:
            df['7d Sparkline'] = ""
            
        return df
    except Exception as e:
        st.error(f"Error fetching or processing market data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_data(coin_id: str, vs_currency: str, days: int = 30):
    try:
        chart = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
        if not chart or 'prices' not in chart: return pd.DataFrame()
        df = pd.DataFrame(chart['prices'], columns=['timestamp','price'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['price'] = pd.to_numeric(df['price'], errors='coerce') # Ensure price is numeric
        return df[['date','price']].dropna()
    except Exception as e:
        st.error(f"Error fetching historical data for {coin_id}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_ohlc_data(coin_id: str, vs_currency: str, days: int = 30):
    try:
        data = cg.get_coin_ohlc_by_id(id=coin_id, vs_currency=vs_currency, days=days)
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data, columns=['timestamp','open','high','low','close'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce') # Ensure numeric
        return df[['date','open','high','low','close']].dropna()
    except Exception as e:
        st.error(f"Error fetching OHLC data for {coin_id}: {e}")
        return pd.DataFrame()

# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100) # Example image
    st.header("⚙️ Settings")
    try:
        supported_currencies_list = cg.get_supported_vs_currencies()
        if supported_currencies_list:
            supported = sorted([str(c).lower() for c in supported_currencies_list]) # Ensure lowercase strings
            cur_idx = supported.index('usd') if 'usd' in supported else 0
        else:
            supported = ['usd'] 
            cur_idx = 0
            st.warning("Could not fetch supported currencies. Using USD as default.")
    except Exception as e:
        supported = ['usd'] 
        cur_idx = 0
        st.warning(f"Could not fetch supported currencies (Error: {type(e).__name__}). Using USD.")
        
    currency = st.selectbox('Currency', supported, index=cur_idx, key="currency_select")
    timeframe = st.selectbox('Movers Timeframe', ['24h','7d','30d'], index=1, key="timeframe_select") 
    refresh_interval = st.slider('Refresh Interval (s)', 10, 300, 60, key="refresh_slider")

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
    if df_mov.empty or pct_col not in df_mov.columns:
        st.caption(f"No data available for {title.lower()}.")
        return
    for _,r_mov in df_mov.iterrows(): # Renamed r to r_mov to avoid conflict if debugging
        ch = r_mov.get(pct_col, 0.0) 
        ch = ch if pd.notnull(ch) else 0.0 # Ensure ch is a float
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

# ========================
# DETAIL VIEW
# ========================
def display_coin_details():
    selected_id = st.session_state.selected_coin_id
    if selected_id is None or 'id' not in df.columns: # Check df has 'id' column
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
    coin_id_detail = coin.get('id', 'unknown') # Use the id from the coin data for consistency

    st.subheader(f"{coin_name_detail} ({coin_symbol_detail})")
    if st.button("⬅️ Back to Overview", key=f"back_button_{coin_id_detail}"): 
        st.session_state.selected_coin_id=None
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
    c1,c2 = st.columns(2)
    
    current_price_val = coin.get('current_price', 0.0); current_price_val = current_price_val if pd.notnull(current_price_val) else 0.0
    change_24h_val = coin.get('24h %', 0.0); change_24h_val = change_24h_val if pd.notnull(change_24h_val) else 0.0
    market_cap_val = coin.get('market_cap', 0); market_cap_val = market_cap_val if pd.notnull(market_cap_val) else 0
    total_volume_val = coin.get('total_volume', 0); total_volume_val = total_volume_val if pd.notnull(total_volume_val) else 0
    
    c1.metric("Price", f"{current_price_val:,.4f} {currency.upper()}", f"{change_24h_val:.2f}%")
    c2.metric("Market Cap", f"${market_cap_val:,}" if currency.lower() == 'usd' else f"{market_cap_val:,} {currency.upper()}")
    c1.metric("24h Vol", f"${total_volume_val:,}" if currency.lower() == 'usd' else f"{total_volume_val:,} {currency.upper()}")
    c2.metric("Rank", f"#{coin.get('market_cap_rank', 'N/A')}")

# ========================
# MARKET OVERVIEW (incorporates fixes for NameError and idxmax)
# ========================
def display_market_overview():
    st.subheader("Key Metrics")
    b_col, e_col, t_col = st.columns(3)

    if 'Symbol' in df.columns and not df.empty:
        btc_df = df[df['Symbol']=='BTC']
        if not btc_df.empty:
            btc = btc_df.iloc[0]
            btc_price = btc.get('current_price', 0); btc_price = btc_price if pd.notnull(btc_price) else 0
            btc_change = btc.get('24h %', 0); btc_change = btc_change if pd.notnull(btc_change) else 0
            b_col.metric(f"BTC Price", f"{btc_price:,.2f} {currency.upper()}", f"{btc_change:.2f}%")
        else:
            b_col.metric(f"BTC Price", "N/A", "N/A")

        eth_df = df[df['Symbol']=='ETH']
        if not eth_df.empty:
            eth = eth_df.iloc[0]
            eth_price = eth.get('current_price', 0); eth_price = eth_price if pd.notnull(eth_price) else 0
            eth_change = eth.get('24h %', 0); eth_change = eth_change if pd.notnull(eth_change) else 0
            e_col.metric(f"ETH Price", f"{eth_price:,.2f} {currency.upper()}", f"{eth_change:.2f}%")
        else:
            e_col.metric(f"ETH Price", "N/A", "N/A")
    else:
        b_col.metric(f"BTC Price", "N/A", "Data Error")
        e_col.metric(f"ETH Price", "N/A", "Data Error")
        
    if '24h %' in df.columns and not df.empty and not df['24h %'].isna().all():
        try:
            df_numeric_24h = df.copy() # Work on a copy
            df_numeric_24h['24h %'] = pd.to_numeric(df_numeric_24h['24h %'], errors='coerce')
            
            if not df_numeric_24h['24h %'].isna().all(): # Check if there are any non-NaN values
                top24_idx = df_numeric_24h['24h %'].idxmax()
                top24 = df.loc[top24_idx] 
                top24_change = top24.get('24h %', 0.0); top24_change = top24_change if pd.notnull(top24_change) else 0.0
                t_col.metric(f"Top 24h Gainer", f"{top24.get('name', 'N/A')}", f"{top24_change:.2f}%")
            else:
                t_col.metric(f"Top 24h Gainer", "N/A", "No valid gainers")
        except ValueError: 
            t_col.metric(f"Top 24h Gainer", "N/A", "Error finding gainer")
    else:
        t_col.metric(f"Top 24h Gainer", "N/A", "Data unavailable")
    st.markdown("---")

    col_map = {'24h':'24h %','7d':'7d %','30d':'30d %'}
    pc = col_map.get(timeframe, '24h %') 
    st.subheader(f"Top Movers ({timeframe})")
    
    if pc in df.columns and not df.empty and not df[pc].isna().all():
        df_copy = df.copy() 
        df_copy[pc] = pd.to_numeric(df_copy[pc], errors='coerce').fillna(0.0)
        g = df_copy.sort_values(pc, ascending=False).head(10)
        l = df_copy.sort_values(pc, ascending=True).head(10)
    else:
        g, l = pd.DataFrame(), pd.DataFrame() 
        st.caption(f"Data for {timeframe} movers not available or column '{pc}' is missing/empty.")

    gc, lc = st.columns(2)
    with gc: display_market_movers(g, f"Gainers ({timeframe})", "🚀", pc)
    with lc: display_market_movers(l, f"Losers ({timeframe})", "📉", pc)
    st.markdown("---")

    st.subheader("Market Overview")
    
    tbl_data = df.head(50) 
    if tbl_data.empty:
        st.info("No market data to display in the overview table.") 
        return

    header_cols_spec = [0.4, 2.2, 1.5, 0.8, 1.8, 1.8] 
    header_cols = st.columns(header_cols_spec)
    headers = ["#", "Coin", f"Price ({currency.upper()})", "24h %", "Market Cap", "7d Sparkline"]
    for col, header_text in zip(header_cols, headers):
        col.markdown(f"**{header_text}**")

    for index, r_row in tbl_data.iterrows(): # Renamed r to r_row
        row_cols = st.columns(header_cols_spec) 
        
        if not isinstance(r_row, pd.Series):
            # This case should ideally not happen with df.iterrows()
            continue

        row_cols[0].write(str(r_row.get('market_cap_rank', 'N/A')))
        
        coin_id_tbl = str(r_row.get('id', f"unknown_{index}")) # Ensure coin_id is a string
        coin_name_tbl = str(r_row.get('name', 'N/A'))
        coin_symbol_tbl = str(r_row.get('Symbol', 'N/A'))
        
        button_key = f"select_{coin_id_tbl}_{index}" 
        coin_label = f"{coin_name_tbl} ({coin_symbol_tbl})"

        if row_cols[1].button(coin_label, key=button_key, help=f"View details for {coin_name_tbl}"):
            st.session_state.selected_coin_id = coin_id_tbl 
            st.rerun()
            
        current_price_val_row = r_row.get('current_price', 0.0); current_price_val_row = current_price_val_row if pd.notnull(current_price_val_row) else 0.0
        row_cols[2].write(f"{current_price_val_row:,.4f}")
        
        change_24h_tbl = r_row.get('24h %', 0.0); change_24h_tbl = change_24h_tbl if pd.notnull(change_24h_tbl) else 0.0
        clr_tbl = '#4CAF50' if change_24h_tbl >= 0 else '#F44336'
        row_cols[3].markdown(f"<div style='color:{clr_tbl}; font-weight:bold; text-align:left;'>{change_24h_tbl:+.2f}%</div>", unsafe_allow_html=True)
        
        market_cap_val_row = r_row.get('market_cap', 0); market_cap_val_row = market_cap_val_row if pd.notnull(market_cap_val_row) else 0
        row_cols[4].write(f"${market_cap_val_row:,}" if currency.lower() == 'usd' else f"{market_cap_val_row:,} {currency.upper()}")
        
        sparkline_html = r_row.get('7d Sparkline', '')
        if sparkline_html:
            row_cols[5].markdown(f"<img src='{sparkline_html}' alt='7d sparkline for {coin_name_tbl}'>", unsafe_allow_html=True)
        else:
            row_cols[5].caption("N/A")
        st.markdown("<hr style='margin-top:0.3rem; margin-bottom:0.3rem; border-top: 1px solid #333;'>", unsafe_allow_html=True)


# ================
# MAIN
# ================
if df.empty:
    st.warning("Unable to load market data. Please check your internet connection, ensure the CoinGecko API is accessible, or try refreshing the page after a few moments.")
    if st.button("🔄 Try Refreshing Data", key="refresh_data_button"):
        # Clearing only data cache. Resource cache (cg client) should persist.
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
        # Create a list of unique coins for the multiselect
        # Using a dictionary to map unique names to their first occurring ID for selection stability
        # then providing list of IDs to multiselect and using names for display
        unique_names_to_ids = {name: coin_id for coin_id, name in df[['id', 'name']].drop_duplicates('name', keep='first').values}
        # Options for multiselect will be the IDs, format_func will show the names
        alert_coin_options = {coin_id: name for name, coin_id in unique_names_to_ids.items()}


        if not alert_coin_options:
            st.info("No coins available for setting alerts.")
        else:
            selected_coin_ids_for_alert = st.multiselect(
                'Monitor Coins', 
                options=list(alert_coin_options.keys()), 
                format_func=lambda coin_id: alert_coin_options.get(coin_id, str(coin_id)), # Show name, fallback to id
                key="alert_multiselect"
            )
            
            for coin_id_watched in selected_coin_ids_for_alert:
                # Get the latest data for the watched coin from the main DataFrame 'df'
                coin_data_series_list = df[df['id'] == coin_id_watched]
                if not coin_data_series_list.empty:
                    cd = coin_data_series_list.iloc[0]
                    coin_name_watched = str(cd.get('name', coin_id_watched)) 
                    current_price_alert = cd.get('current_price', 0.0)
                    current_price_alert = float(current_price_alert) if pd.notnull(current_price_alert) else 0.0

                    target_price_key = f"alert_target_{coin_id_watched}" 
                    
                    if target_price_key not in st.session_state:
                        st.session_state[target_price_key] = float(current_price_alert * 1.05) if current_price_alert > 0 else 0.01

                    widget_key_alert = f"user_alert_input_{coin_id_watched}"
                    
                    user_target_price = st.number_input(
                        f"Target for {coin_name_watched} (now: {current_price_alert:,.4f} {currency.upper()})",
                        value=float(st.session_state[target_price_key]), 
                        min_value=0.0,
                        format="%.6f", # Allow more precision for target price
                        key=widget_key_alert 
                    )
                    
                    st.session_state[target_price_key] = user_target_price 
                    
                    alert_hit_key = f"alert_hit_{coin_id_watched}_{user_target_price}" # Key to remember if this specific alert fired
                    
                    if current_price_alert > 0 and user_target_price > 0 and current_price_alert >= user_target_price:
                        if not st.session_state.get(alert_hit_key, False): # Check if already fired
                            st.success(f"🔔 ALERT! {coin_name_watched} reached {user_target_price:,.4f} {currency.upper()}!")
                            st.balloons()
                            st.session_state[alert_hit_key] = True # Mark as fired
                    elif st.session_state.get(alert_hit_key, False) and current_price_alert < user_target_price:
                        # Optionally reset the "fired" status if price drops below target again
                        st.session_state[alert_hit_key] = False
                else:
                    st.caption(f"Data for coin ID {coin_id_watched} (for alert) not found in current dataset.")
    else:
        st.info("Market data not fully loaded, cannot set alerts yet.")

# auto-refresh logic
if time.time() - st.session_state.get('last_refresh', 0) > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()
