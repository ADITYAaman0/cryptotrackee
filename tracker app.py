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
        # You might want to log this error or show a silent failure
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
    try:
        buf = BytesIO(); fig.write_image(buf, format='png', engine='kaleido')
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    except Exception: # Catch error if kaleido is not available or image generation fails
        return ""


@st.cache_data(ttl=60)
def load_market_data(vs_currency: str):
    try:
        data = cg.get_coins_markets(
            vs_currency=vs_currency, order='market_cap_desc', per_page=250,
            sparkline=True, price_change_percentage='24h,7d,30d'
        )
        if not data: # Handle empty API response
            st.warning(f"No market data received from API for currency: {vs_currency}")
            return pd.DataFrame()
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching market data: {e}")
        return pd.DataFrame()

    # Safely create new columns with fallbacks
    df['24h %'] = df.get('price_change_percentage_24h_in_currency', pd.Series(dtype='float')).fillna(0)
    df['7d %']  = df.get('price_change_percentage_7d_in_currency', pd.Series(dtype='float')).fillna(0)
    df['30d %'] = df.get('price_change_percentage_30d_in_currency', pd.Series(dtype='float')).fillna(0)
    df['Symbol'] = df.get('symbol', pd.Series(dtype='object')).str.upper().fillna('N/A')
    df['Logo']   = df.get('image', pd.Series(dtype='object')).fillna('')
    
    if 'sparkline_in_7d' in df.columns:
        df['7d Sparkline'] = df['sparkline_in_7d'].apply(
            lambda x: create_sparkline(x.get('price', [])) if isinstance(x, dict) else ""
        )
    else:
        df['7d Sparkline'] = ""
        
    return df

@st.cache_data(ttl=3600)
def get_historical_data(coin_id: str, vs_currency: str, days: int = 30):
    try:
        chart = cg.get_coin_market_chart_by_id(coin_id, vs_currency, days)
        if not chart or 'prices' not in chart: return pd.DataFrame()
        df = pd.DataFrame(chart['prices'], columns=['timestamp','price'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df[['date','price']]
    except Exception as e:
        st.error(f"Error fetching historical data for {coin_id}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_ohlc_data(coin_id: str, vs_currency: str, days: int = 30):
    try:
        data = cg.get_coin_ohlc_by_id(coin_id, vs_currency, days)
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data, columns=['timestamp','open','high','low','close'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df[['date','open','high','low','close']]
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
            supported = sorted(supported_currencies_list)
            cur_idx = supported.index('usd') if 'usd' in supported else 0
        else:
            supported = ['usd'] # Fallback
            cur_idx = 0
            st.warning("Could not fetch supported currencies. Using USD as default.")
    except Exception as e:
        supported = ['usd'] # Fallback
        cur_idx = 0
        st.warning(f"Could not fetch supported currencies (Error: {e}). Using USD.")
        
    currency = st.selectbox('Currency', supported, index=cur_idx, key="currency_select")
    timeframe = st.selectbox('Movers Timeframe', ['24h','7d','30d'], index=1, key="timeframe_select") # Default to 7d
    refresh_interval = st.slider('Refresh Interval (s)', 10,300,60, key="refresh_slider")

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
    for _,r in df_mov.iterrows():
        ch = r.get(pct_col, 0.0) # Ensure ch always has a float value
        clr = '#4CAF50' if ch>=0 else '#F44336'
        st.markdown(f"""
            <div class='mover-row'>
                <img src='{r.get('Logo', '')}' width='30' alt='{r.get('name', '')} logo' style='vertical-align:middle; margin-right:5px;'>
                <span class='mover-name'>{r.get('name', 'N/A')}</span>
                <span style='flex-grow:1;text-align:right;color:{clr};font-weight:bold;'>
                    {ch:+.2f}%
                </span>
            </div>
        """, unsafe_allow_html=True)

# ========================
# DETAIL VIEW
# ========================
def display_coin_details():
    if 'id' not in df.columns or st.session_state.selected_coin_id is None:
        st.warning("Coin data or selection is invalid. Returning to overview.")
        st.session_state.selected_coin_id = None # Reset selection
        st.rerun() # Use rerun to refresh the page state correctly
        return

    sel = df[df['id']==st.session_state.selected_coin_id]
    if sel.empty:
        st.warning("Selected coin not found in the current dataset. It might have been removed or filtered out. Returning to overview.")
        st.session_state.selected_coin_id = None
        st.rerun()
        return 
        
    coin = sel.iloc[0]
    st.subheader(f"{coin.get('name', 'N/A')} ({coin.get('Symbol', 'N/A')})")
    if st.button("⬅️ Back to Overview", key=f"back_button_{coin.get('id')}"): 
        st.session_state.selected_coin_id=None
        st.rerun() # Use rerun to refresh the page state

    chart_type = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"], key=f"chart_type_{coin.get('id')}")
    days = st.slider("History (days)", min_value=7, max_value=365, value=30, key=f"days_{coin.get('id')}")

    fig_data_loaded = False
    if chart_type == "Line":
        hist = get_historical_data(coin['id'], currency, days)
        if not hist.empty:
            fig = px.line(hist, x='date', y='price', title=f"{coin['name']} Price (Last {days}d)",
                          labels={'price':f'Price ({currency.upper()})','date':'Date'})
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF", title_font_color="#FFFFFF")
            fig.update_xaxes(showgrid=False, color="#FFFFFF")
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#FFFFFF")
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
    else: # Candlestick or OHLC
        ohlc = get_ohlc_data(coin['id'], currency, days)
        if not ohlc.empty:
            if chart_type == "Candlestick":
                fig = go.Figure(data=[
                    go.Candlestick(
                        x=ohlc['date'], open=ohlc['open'], high=ohlc['high'],
                        low=ohlc['low'], close=ohlc['close']
                    )
                ])
            else: # OHLC
                fig = go.Figure(data=[
                    go.Ohlc(
                        x=ohlc['date'], open=ohlc['open'], high=ohlc['high'],
                        low=ohlc['low'], close=ohlc['close']
                    )
                ])
            fig.update_layout(title=f"{coin['name']} {chart_type} Chart (Last {days}d)",
                              xaxis_rangeslider_visible=False, # Cleaner look
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF", title_font_color="#FFFFFF")
            fig.update_xaxes(showgrid=False, color="#FFFFFF")
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#FFFFFF")
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
    
    if not fig_data_loaded:
        st.info(f"No chart data to display for {coin.get('name', 'N/A')} for the selected period or type.")

    st.subheader("Info & Metrics")
    c1,c2 = st.columns(2)
    # Ensure values are numbers before formatting
    current_price_val = coin.get('current_price', 0) if pd.notnull(coin.get('current_price')) else 0
    change_24h_val = coin.get('24h %', 0) if pd.notnull(coin.get('24h %')) else 0
    market_cap_val = coin.get('market_cap', 0) if pd.notnull(coin.get('market_cap')) else 0
    total_volume_val = coin.get('total_volume', 0) if pd.notnull(coin.get('total_volume')) else 0
    
    c1.metric("Price", f"{current_price_val:,.4f} {currency.upper()}", f"{change_24h_val:.2f}%")
    c2.metric("Market Cap", f"${market_cap_val:,}" if currency.lower() == 'usd' else f"{market_cap_val:,} {currency.upper()}")
    c1.metric("24h Vol", f"${total_volume_val:,}" if currency.lower() == 'usd' else f"{total_volume_val:,} {currency.upper()}")
    c2.metric("Rank", f"#{coin.get('market_cap_rank', 'N/A')}")

# ========================
# OVERVIEW
# ========================
def display_market_overview():
    st.subheader("Key Metrics")
    b_col, e_col, t_col = st.columns(3)

    if 'Symbol' in df.columns and not df.empty:
        btc_df = df[df['Symbol']=='BTC']
        if not btc_df.empty:
            btc = btc_df.iloc[0]
            btc_price = btc.get('current_price', 0) if pd.notnull(btc.get('current_price')) else 0
            btc_change = btc.get('24h %', 0) if pd.notnull(btc.get('24h %')) else 0
            b_col.metric(f"BTC Price", f"{btc_price:,.2f} {currency.upper()}", f"{btc_change:.2f}%")
        else:
            b_col.metric(f"BTC Price", "N/A", "N/A")

        eth_df = df[df['Symbol']=='ETH']
        if not eth_df.empty:
            eth = eth_df.iloc[0]
            eth_price = eth.get('current_price', 0) if pd.notnull(eth.get('current_price')) else 0
            eth_change = eth.get('24h %', 0) if pd.notnull(eth.get('24h %')) else 0
            e_col.metric(f"ETH Price", f"{eth_price:,.2f} {currency.upper()}", f"{eth_change:.2f}%")
        else:
            e_col.metric(f"ETH Price", "N/A", "N/A")
    else:
        b_col.metric(f"BTC Price", "N/A", "Data Error")
        e_col.metric(f"ETH Price", "N/A", "Data Error")
        
    if '24h %' in df.columns and not df.empty and not df['24h %'].isna().all():
        try:
            top24 = df.loc[df['24h %'].idxmax()]
            top24_change = top24.get('24h %', 0) if pd.notnull(top24.get('24h %')) else 0
            t_col.metric(f"Top 24h Gainer", f"{top24.get('name', 'N/A')}", f"{top24_change:.2f}%")
        except ValueError: 
            t_col.metric(f"Top 24h Gainer", "N/A", "Error")
    else:
        t_col.metric(f"Top 24h Gainer", "N/A", "N/A")
    st.markdown("---")

    col_map = {'24h':'24h %','7d':'7d %','30d':'30d %'}
    pc = col_map.get(timeframe, '24h %') 
    st.subheader(f"Top Movers ({timeframe})")
    
    if pc in df.columns and not df.empty and not df[pc].isna().all():
        # Ensure the column is numeric for sorting
        df_copy = df.copy() # Work on a copy to avoid SettingWithCopyWarning
        df_copy[pc] = pd.to_numeric(df_copy[pc], errors='coerce').fillna(0)
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

    header_cols_spec = [0.5, 2.5, 1.5, 1, 2, 2] # Adjusted Coin and Sparkline column width slightly
    header_cols = st.columns(header_cols_spec)
    headers = ["#", "Coin", f"Price ({currency.upper()})", "24h %", "Market Cap", "7d Sparkline"]
    for col, header_text in zip(header_cols, headers):
        col.markdown(f"**{header_text}**")

    for index, r in tbl_data.iterrows(): # Using index for a more robust unique key
        row_cols = st.columns(header_cols_spec) 
        row_cols[0].write(str(r.get('market_cap_rank', 'N/A')))
        
        coin_id = r.get('id', f"unknown_{index}")
        coin_name = r.get('name', 'N/A')
        coin_symbol = r.get('Symbol', 'N/A')
        button_key = f"select_{coin_id}" 
        coin_label = f"{coin_name} ({coin_symbol})"

        # Use a container for the button to manage layout if needed, or directly place button.
        # Adding the image next to the button requires more complex HTML or careful column use.
        # For simplicity, button first:
        if row_cols[1].button(coin_label, key=button_key, help=f"View details for {coin_name}"):
            st.session_state.selected_coin_id = coin_id # Use the actual ID
            st.rerun()
            
        current_price_val_row = r.get('current_price', 0) if pd.notnull(r.get('current_price')) else 0
        row_cols[2].write(f"{current_price_val_row:,.4f}")
        
        change_24h = r.get('24h %', 0.0) if pd.notnull(r.get('24h %')) else 0.0
        clr = '#4CAF50' if change_24h >= 0 else '#F44336'
        row_cols[3].markdown(f"<div style='color:{clr}; font-weight:bold; text-align:left;'>{change_24h:+.2f}%</div>", unsafe_allow_html=True)
        
        market_cap_val_row = r.get('market_cap', 0) if pd.notnull(r.get('market_cap')) else 0
        row_cols[4].write(f"${market_cap_val_row:,}" if currency.lower() == 'usd' else f"{market_cap_val_row:,} {currency.upper()}")
        
        sparkline_html = r.get('7d Sparkline', '')
        if sparkline_html:
            row_cols[5].markdown(f"<img src='{sparkline_html}' alt='7d sparkline for {coin_name}'>", unsafe_allow_html=True)
        else:
            row_cols[5].caption("N/A")
        # Add a thin line after each row for better separation
        st.markdown("<hr style='margin-top:0.3rem; margin-bottom:0.3rem; border-top: 1px solid #333;'>", unsafe_allow_html=True)


# ================
# MAIN
# ================
if df.empty:
    st.warning("Unable to load market data. Please check your internet connection, ensure the CoinGecko API is accessible, or try refreshing the page after a few moments.")
    if st.button("🔄 Try Refreshing Data"):
        st.cache_data.clear() # Clear data cache
        st.cache_resource.clear() # Clear resource cache (like CG client if needed, though usually not for this)
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
        # Create a list of tuples (id, name) for multiselect, ensuring unique IDs are used internally
        # and unique names are shown to the user.
        # If names are not unique, the first occurrence's ID will be used by this mapping.
        coin_options_for_alert = df[['id', 'name']].drop_duplicates(subset=['name']).set_index('id')['name'].to_dict()
        
        if not coin_options_for_alert:
            st.info("No coins available for setting alerts (data might be sparse).")
        else:
            # Store selected IDs, show names to user
            selected_coin_ids_for_alert = st.multiselect(
                'Monitor Coins', 
                options=list(coin_options_for_alert.keys()), 
                format_func=lambda coin_id: coin_options_for_alert[coin_id], # Show name
                key="alert_multiselect"
            )
            
            for coin_id_watched in selected_coin_ids_for_alert:
                coin_data_series = df[df['id']==coin_id_watched]
                if not coin_data_series.empty:
                    cd = coin_data_series.iloc[0]
                    coin_name_watched = cd.get('name', coin_id_watched) # Get name for display
                    current_price = cd.get('current_price', 0.0)
                    if not isinstance(current_price, (int, float)): current_price = 0.0 # Ensure numeric

                    target_price_key = f"alert_target_{coin_id_watched}" 
                    
                    if target_price_key not in st.session_state:
                        st.session_state[target_price_key] = float(current_price * 1.05) if current_price > 0 else 0.01 # Default 5% higher or small value

                    # Use a unique key for each number_input widget
                    widget_key = f"user_alert_input_{coin_id_watched}"
                    
                    user_target_price = st.number_input(
                        f"Target for {coin_name_watched} (now: {current_price:,.4f} {currency.upper()})",
                        value=float(st.session_state[target_price_key]), # Ensure float for value
                        min_value=0.0,
                        format="%.4f", 
                        key=widget_key 
                    )
                    
                    st.session_state[target_price_key] = user_target_price # Persist changed target
                    
                    if current_price > 0 and user_target_price > 0 and current_price >= user_target_price:
                        alert_triggered_key = f"alert_triggered_{coin_id_watched}_{user_target_price}"
                        # Trigger alert only once for a specific target price unless reset
                        if alert_triggered_key not in st.session_state:
                            st.success(f"🔔 ALERT! {coin_name_watched} reached {user_target_price:,.4f} {currency.upper()}!")
                            st.balloons()
                            st.session_state[alert_triggered_key] = True # Mark as triggered
                else:
                    st.caption(f"Data for coin ID {coin_id_watched} (for alert) not found.")
    else:
        st.info("Market data not fully loaded, cannot set alerts yet.")

# auto-refresh logic
if time.time() - st.session_state.get('last_refresh', 0) > refresh_interval: # Use .get for safety
    st.session_state.last_refresh = time.time()
    st.rerun()
