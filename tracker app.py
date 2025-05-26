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
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    try:
        supported = sorted(cg.get_supported_vs_currencies())
        cur_idx = supported.index('usd') if 'usd' in supported else 0
    except Exception:
        supported = ['usd'] # Fallback
        cur_idx = 0
        st.warning("Could not fetch supported currencies. Using USD.")
        
    currency = st.selectbox('Currency', supported, index=cur_idx)
    timeframe = st.selectbox('Movers Timeframe', ['24h','7d','30d'], index=1)
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
        st.caption("No data available for movers.")
        return
    for _,r in df_mov.iterrows():
        ch = r.get(pct_col, 0.0)
        clr = '#4CAF50' if ch>=0 else '#F44336'
        st.markdown(f"""
            <div class='mover-row'>
              <img src='{r.get('Logo', '')}' width='30' alt='{r.get('name', '')} logo'>
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
        st.warning("Coin data or selection is invalid.")
        st.session_state.selected_coin_id = None # Reset selection
        st.rerun()
        return

    sel = df[df['id']==st.session_state.selected_coin_id]
    if sel.empty:
        st.warning("Coin not available in current dataset. Returning...")
        st.session_state.selected_coin_id = None
        st.rerun()
        return # Important to return here
        
    coin = sel.iloc[0]
    st.subheader(f"{coin.get('name', 'N/A')} ({coin.get('Symbol', 'N/A')})")
    if st.button("⬅️ Back"): 
        st.session_state.selected_coin_id=None
        st.rerun()

    chart_type = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"], key=f"chart_type_{coin.get('id')}")
    days = st.slider("History (days)", 7,90,30, key=f"days_{coin.get('id')}")

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
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFFFFF", title_font_color="#FFFFFF")
            fig.update_xaxes(showgrid=False, color="#FFFFFF")
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#FFFFFF")
            st.plotly_chart(fig, use_container_width=True)
            fig_data_loaded = True
    
    if not fig_data_loaded:
        st.info("No chart data to display for the selected period or type.")

    st.subheader("Info & Metrics")
    c1,c2 = st.columns(2)
    c1.metric("Price", f"{coin.get('current_price', 0):,.4f} {currency.upper()}", f"{coin.get('24h %', 0):.2f}%")
    c2.metric("Market Cap", f"${coin.get('market_cap', 0):,}" if currency.lower() == 'usd' else f"{coin.get('market_cap', 0):,} {currency.upper()}")
    c1.metric("24h Vol", f"${coin.get('total_volume', 0):,}" if currency.lower() == 'usd' else f"{coin.get('total_volume', 0):,} {currency.upper()}")
    c2.metric("Rank", f"#{coin.get('market_cap_rank', 'N/A')}")

# ========================
# OVERVIEW
# ========================
def display_market_overview():
    st.subheader("Key Metrics")
    b_col, e_col, t_col = st.columns(3)

    if 'Symbol' in df.columns:
        btc_df = df[df['Symbol']=='BTC']
        if not btc_df.empty:
            btc = btc_df.iloc[0]
            b_col.metric(f"BTC", f"{btc.get('current_price', 0):,.2f} {currency.upper()}", f"{btc.get('24h %', 0):.2f}%")
        else:
            b_col.metric(f"BTC", "N/A", "N/A")

        eth_df = df[df['Symbol']=='ETH']
        if not eth_df.empty:
            eth = eth_df.iloc[0]
            e_col.metric(f"ETH", f"{eth.get('current_price', 0):,.2f} {currency.upper()}", f"{eth.get('24h %', 0):.2f}%")
        else:
            e_col.metric(f"ETH", "N/A", "N/A")
    else:
        b_col.metric(f"BTC", "N/A", "Data Error")
        e_col.metric(f"ETH", "N/A", "Data Error")
        
    if '24h %' in df.columns and not df.empty and not df['24h %'].isna().all():
        try:
            top24 = df.loc[df['24h %'].idxmax()]
            t_col.metric(f"Top 24h Gainer", f"{top24.get('name', 'N/A')}", f"{top24.get('24h %', 0):.2f}%")
        except ValueError: # Handles case where '24h %' might be all NaN or idxmax fails
             t_col.metric(f"Top 24h Gainer", "N/A", "Error")
    else:
        t_col.metric(f"Top 24h Gainer", "N/A", "N/A")
    st.markdown("---")

    col_map = {'24h':'24h %','7d':'7d %','30d':'30d %'}
    pc = col_map.get(timeframe, '24h %') # Default to '24h %' if timeframe somehow invalid
    st.subheader(f"Top Movers ({timeframe})")
    
    if pc in df.columns and not df[pc].isna().all():
        g = df.sort_values(pc, ascending=False).head(10)
        l = df.sort_values(pc, ascending=True).head(10)
    else:
        g, l = pd.DataFrame(), pd.DataFrame() # Empty dataframes if column is missing
        st.caption(f"Data for {timeframe} movers not available.")

    gc, lc = st.columns(2)
    with gc: display_market_movers(g, f"Gainers ({timeframe})", "🚀", pc)
    with lc: display_market_movers(l, f"Losers ({timeframe})", "📉", pc)
    st.markdown("---")

    st.subheader("Market Overview")
    # Use a subset of df for display to avoid issues if df is very large after filtering, though head(50) manages this.
    tbl_data = df.head(50) 
    if tbl_data.empty:
        st.info("No market data to display in the overview table.")
        return

    # Define headers for the custom table
    header_cols = st.columns([0.5, 2, 1.5, 1, 2, 2.5]) # Adjusted Price column width
    headers = ["#", "Coin", f"Price ({currency.upper()})", "24h %", "Market Cap", "7d Sparkline"]
    for col, header_text in zip(header_cols, headers):
        col.markdown(f"**{header_text}**")

    for _, r in tbl_data.iterrows():
        row_cols = st.columns([0.5, 2, 1.5, 1, 2, 2.5]) # Must match header_cols definition
        row_cols[0].write(str(r.get('market_cap_rank', 'N/A')))
        
        # Button for coin selection
        button_key = f"select_{r.get('id', r.get('name', 'unknown'))}" # Ensure key is unique
        coin_label = f"{r.get('name', 'N/A')} ({r.get('Symbol', 'N/A')})"
        if row_cols[1].button(coin_label, key=button_key, help=f"View details for {r.get('name', 'N/A')}"):
            st.session_state.selected_coin_id=r.get('id')
            st.rerun()
            
        row_cols[2].write(f"{r.get('current_price', 0):,.4f}")
        
        change_24h = r.get('24h %', 0.0)
        clr = '#4CAF50' if change_24 >= 0 else '#F44336'
        row_cols[3].markdown(f"<b style='color:{clr};'>{change_24:+.2f}%</b>", unsafe_allow_html=True)
        
        row_cols[4].write(f"${r.get('market_cap', 0):,}" if currency.lower() == 'usd' else f"{r.get('market_cap', 0):,} {currency.upper()}")
        
        sparkline_html = r.get('7d Sparkline', '')
        if sparkline_html:
            row_cols[5].markdown(f"<img src='{sparkline_html}' alt='7d sparkline for {r.get('name', '')}'>", unsafe_allow_html=True)
        else:
            row_cols[5].caption("N/A")


# ================
# MAIN
# ================
if df.empty:
    st.warning("Unable to load market data. Please check your connection or try refreshing.")
    # Optionally, attempt a manual refresh button here or guide user
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
    if not df.empty and 'name' in df.columns and 'current_price' in df.columns:
        # Ensure 'name' column has unique values for multiselect if used as options
        # If names are not unique, this could cause issues. IDs are better for selection.
        # For simplicity, using names as provided in original code.
        available_coins_for_alert = df['name'].drop_duplicates().tolist()
        if not available_coins_for_alert:
            st.info("No coins available for setting alerts.")
        else:
            watch = st.multiselect('Monitor Coins', available_coins_for_alert, key="alert_multiselect")
            for coin_name_watched in watch:
                coin_data_series = df[df['name']==coin_name_watched]
                if not coin_data_series.empty:
                    cd = coin_data_series.iloc[0]
                    current_price = cd.get('current_price', 0.0)
                    
                    # State key for this coin's target price
                    target_price_key = f"alert_target_{cd.get('id', coin_name_watched)}" 
                    
                    # Initialize target in session state if not present
                    if target_price_key not in st.session_state:
                        st.session_state[target_price_key] = float(current_price * 1.05) if current_price > 0 else 0.0

                    # User input for target price, value taken from session_state
                    user_target_price = st.number_input(
                        f"Alert for {coin_name_watched} (current: {current_price:,.4f})",
                        value=float(st.session_state[target_price_key]),
                        min_value=0.0,
                        format="%.4f", # Allow appropriate precision
                        key=f"user_alert_input_{cd.get('id', coin_name_watched)}" # Unique key for the widget
                    )
                    
                    # Update session_state with the value from number_input
                    st.session_state[target_price_key] = user_target_price
                    
                    # Check alert condition using the persisted target from session_state
                    if current_price > 0 and st.session_state[target_price_key] > 0 and current_price >= st.session_state[target_price_key]:
                        st.success(f"🔔 ALERT! {coin_name_watched} reached {st.session_state[target_price_key]:,.4f} {currency.upper()}!")
                        st.balloons()
                        # Optionally, clear the alert or the target once hit
                        # del st.session_state[target_price_key] # Example: remove to stop further alerts for this target
    else:
        st.info("Market data not loaded, cannot set alerts.")

# auto-refresh
if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()
