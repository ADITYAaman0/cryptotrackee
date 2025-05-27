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
    except:
        return None

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@400;700&family=Orbitron:wght@500&display=swap');
.central-header {font-family:'Orbitron'; font-size:3.5rem; text-align:center; 
  background:linear-gradient(45deg,#4CAF50,#2196F3); -webkit-background-clip:text; 
  -webkit-text-fill-color:transparent; margin-bottom:20px; text-shadow:2px 2px 4px rgba(0,0,0,0.3);}
.stMetric {background:#262730;border-radius:12px;padding:20px;border:1px solid #4CAF50;box-shadow:0 4px 8px rgba(76,175,80,0.2);}
.mover-header {font-family:'Kanit';font-size:1.5rem;color:#FFF;padding-bottom:10px;border-bottom:2px solid #4CAF50;}
.mover-row {display:flex;align-items:center;margin-bottom:4px;}
.mover-name {font-family:'Kanit';font-weight:bold;margin-left:8px;color:#FFF;}
.stTextInput > div > div > input {
    border-radius:25px;border:2px solid #4CAF50;padding:10px 15px;
    box-shadow:0 4px 8px rgba(0,0,0,0.2);transition:0.3s;color:#E0E0E0;background:#1A1A1A;
}
.stTextInput > div > div > input:focus {border-color:#2196F3;box-shadow:0 4px 12px rgba(33,150,243,0.3);}
.stTextInput label {font-weight:bold;color:#E0E0E0;font-size:1.1rem;margin-bottom:5px;display:block;}
.stButton > button {border-radius:8px;border:1px solid #F44336;background:#F44336;color:#FFF;padding:8px 15px;font-weight:bold;transition:0.2s;}
.stButton > button:hover {background:#D32F2F;border-color:#D32F2F;}
.chart-info-metric {font-size:1.1rem;color:#E0E0E0;margin-right:15px;display:inline-block;}
.chart-info-value {font-weight:bold;}
.change-positive {color:#4CAF50;}
.change-negative {color:#F44336;}
</style>
""", unsafe_allow_html=True)

# Header Lottie + Title
with st.container():
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim:
            st_lottie(anim, height=200)
        st.markdown("<div class='central-header'>CRYPTO TRACKEE</div>", unsafe_allow_html=True)
    st.markdown("---")

# ========================
# FORMAT HELPERS
# ========================
def abbreviate_number(num: float) -> str:
    for unit in ['', 'K', 'M', 'B', 'T']:
        if abs(num) < 1000:
            return f"{num:.2f}{unit}"
        num /= 1000
    return f"{num:.2f}E"

def format_currency(num: float, currency: str) -> str:
    abbr = abbreviate_number(num)
    if currency.lower() == 'usd':
        return f"${abbr}"
    return f"{abbr} {currency.upper()}"

# ========================
# WATCHLIST
# ========================
def init_watchlist():
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []

def toggle_watchlist(cid):
    wl = st.session_state.watchlist
    if cid in wl:
        wl.remove(cid)
    else:
        wl.append(cid)

def display_watchlist(df, cur):
    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Your Watchlist")
    if not st.session_state.watchlist:
        st.sidebar.info("Add coins to your watchlist ★")
        return
    wl_df = df[df['id'].isin(st.session_state.watchlist)]
    for _, r in wl_df.iterrows():
        c1, c2 = st.sidebar.columns([1,4])
        with c1:
            st.image(r['Logo'], width=40)
        pct = r['24h %']; clr = '#4CAF50' if pct>=0 else '#F44336'
        c2.markdown(f"""
            <div style='padding:8px;background:rgba(76,175,80,0.15);border-radius:8px;'>
              <strong style='color:#FFF;'>{r['name']}</strong><br>
              <span style='color:#CCC;'>{r['current_price']:,.4f} {cur.upper()}</span>
              <span style='color:{clr};margin-left:8px;'>{pct:+.2f}%</span>
            </div>
        """, unsafe_allow_html=True)

# ========================
# DATA FETCHING
# ========================
@st.cache_resource
def get_client():
    return CoinGeckoAPI()
cg = get_client()

def create_sparkline(data):
    if not isinstance(data, list) or len(data)<2:
        return ""
    s = pd.to_numeric(pd.Series(data), errors='coerce').dropna().tolist()
    if len(s)<2:
        return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(s))), y=s, mode='lines',
        line=dict(color='#4CAF50' if s[-1]>=s[0] else '#F44336', width=2)
    ))
    fig.update_layout(showlegend=False, xaxis_visible=False, yaxis_visible=False,
                      margin=dict(t=0,b=0,l=0,r=0),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      width=150, height=50)
    buf = BytesIO(); fig.write_image(buf, format='png', engine='kaleido')
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
        df['24h %']  = pd.to_numeric(df.get('price_change_percentage_24h_in_currency'), errors='coerce').fillna(0)
        df['7d %']   = pd.to_numeric(df.get('price_change_percentage_7d_in_currency'), errors='coerce').fillna(0)
        df['30d %']  = pd.to_numeric(df.get('price_change_percentage_30d_in_currency'), errors='coerce').fillna(0)
        df['Symbol']= df['symbol'].str.upper()
        df['Logo']  = df['image']
        df['current_price']  = pd.to_numeric(df['current_price'], errors='coerce').fillna(0)
        df['market_cap']      = pd.to_numeric(df['market_cap'], errors='coerce').fillna(0)
        df['total_volume']    = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
        df['market_cap_rank'] = pd.to_numeric(df['market_cap_rank'], errors='coerce').fillna(0).astype(int)
        df['7d Sparkline'] = df['sparkline_in_7d'].apply(
            lambda x: create_sparkline(x['price']) if isinstance(x, dict) and 'price' in x else ""
        )
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_data(cid, vs_currency, days=30):
    try:
        chart = cg.get_coin_market_chart_by_id(id=cid, vs_currency=vs_currency, days=days)
        df2 = pd.DataFrame(chart.get('prices', []), columns=['timestamp','price'])
        df2['date'] = pd.to_datetime(df2['timestamp'], unit='ms')
        return df2[['date','price']].dropna()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_raw_ohlc_data(cid, vs_currency, days):
    try:
        arr = cg.get_coin_ohlc_by_id(id=cid, vs_currency=vs_currency, days=days)
        df3 = pd.DataFrame(arr, columns=['timestamp','open','high','low','close'])
        df3['date'] = pd.to_datetime(df3['timestamp'], unit='ms')
        for c in ['open','high','low','close']:
            df3[c] = pd.to_numeric(df3[c], errors='coerce')
        return df3[['date','open','high','low','close']].dropna()
    except:
        return pd.DataFrame()

def resample_ohlc(df1, interval):
    if df1.empty:
        return df1
    df2 = df1.set_index('date').resample(interval).apply({
        'open':'first','high':'max','low':'min','close':'last'
    }).dropna().reset_index()
    return df2

# ========================
# SIDEBAR SETTINGS
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    try:
        cur_list = cg.get_supported_vs_currencies()
        supported = sorted([c.lower() for c in cur_list])
        idx = supported.index('usd') if 'usd' in supported else 0
    except:
        supported = ['usd']; idx = 0
    currency = st.selectbox("Currency", supported, index=idx)
    timeframe = st.selectbox("Movers Timeframe", ['24h','7d','30d'], index=1)
    refresh_interval = st.slider("Auto-Refresh Interval (s)", 10, 300, 30)

# initialize session
init_watchlist()
if 'selected_coin_id' not in st.session_state:
    st.session_state.selected_coin_id = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# load data & watchlist
df = load_market_data(currency)
display_watchlist(df, currency)

# ========================
# RENDER COINS TABLE
# ========================
def render_coins_table(df_show, cur):
    if df_show.empty:
        st.write("No coins to display.")
        return
    specs = [0.4,2.2,1.5,0.8,1.8,1.8,0.5]
    headers = ["#","Coin",f"Price ({cur.upper()})","24h %","Market Cap","7d Sparkline","★"]
    cols = st.columns(specs)
    for c,h in zip(cols, headers):
        c.markdown(f"**{h}**")
    for idx,r in df_show.iterrows():
        c0,c1,c2,c3,c4,c5,c6 = st.columns(specs)
        cid = r['id']
        with c6:
            icon = "★" if cid in st.session_state.watchlist else "☆"
            if st.button(icon, key=f"star_{cid}_{idx}"):
                toggle_watchlist(cid)
                st.rerun()
        c0.write(r['market_cap_rank'])
        name = f"{r['name']} ({r['Symbol']})"
        logo = r['Logo']
        key_btn = f"btn_{cid}_{idx}"
        if logo:
            c1.markdown(
                f"<img src='{logo}' width=20 style='vertical-align:middle;margin-right:5px;'/>"
                f"<button style='background:none;border:none;color:#FFF;' onclick=\"document.getElementById('{key_btn}').click()\">{name}</button>",
                unsafe_allow_html=True
            )
            if c1.button(" ", key=key_btn, use_container_width=True):
                st.session_state.selected_coin_id = cid
                st.session_state.search_query = ""
                st.rerun()
        else:
            if c1.button(name, key=key_btn):
                st.session_state.selected_coin_id = cid
                st.session_state.search_query = ""
                st.rerun()
        c2.write(f"{r['current_price']:,.4f}")
        pct = r['24h %']; clr = '#4CAF50' if pct>=0 else '#F44336'
        c3.markdown(f"<span style='color:{clr};font-weight:bold'>{pct:+.2f}%</span>", unsafe_allow_html=True)
        c4.write(format_currency(r['market_cap'], cur))
        sp = r['7d Sparkline']
        if sp:
            c5.image(sp, use_container_width=True)
        else:
            c5.write("–")
        st.markdown("<hr style='border-color:#333;margin:4px 0;'>", unsafe_allow_html=True)

# ========================
# OVERVIEW / SEARCH
# ========================
def display_overview():
    # search bar
    q = st.text_input("🔍 Search Coins", value=st.session_state.search_query,
                      placeholder="Name or symbol")
    if q != st.session_state.search_query:
        st.session_state.search_query = q
        st.rerun()

    # if searching
    if st.session_state.search_query.strip():
        st.button("⬅️ Clear Search", on_click=lambda: st.session_state.update(search_query=""))
        st.subheader(f"Results for «{st.session_state.search_query}»")
        mask = (
            df['name'].str.lower().str.contains(q.lower()) |
            df['Symbol'].str.lower().str.contains(q.lower())
        )
        render_coins_table(df[mask], currency)

    else:
        # Key Metrics
        st.subheader("Key Metrics")
        bcol, ecol, tcol = st.columns(3)
        for sym, col in [('BTC',bcol),('ETH',ecol)]:
            sel = df[df['Symbol']==sym]
            if not sel.empty:
                v = sel.iloc[0]['current_price']
                c24 = sel.iloc[0]['24h %']
                col.metric(f"{sym} Price", f"{v:,.2f} {currency.upper()}", f"{c24:+.2f}%")
            else:
                col.metric(f"{sym} Price", "N/A", "N/A")

        # --- Top Gainers / Top Losers ---
        st.markdown("### Movers")
        col_map = {'24h':'24h %', '7d':'7d %', '30d':'30d %'}
        pct_col = col_map.get(timeframe, '24h %')

        top5 = df.nlargest(5, pct_col)
        bot5 = df.nsmallest(5, pct_col)

        left, right = st.columns(2)
        with left:
            st.markdown(f"**Top Gainers ({timeframe})**")
            for _, r in top5.iterrows():
                p = r[pct_col]; clr = '#4CAF50' if p>=0 else '#F44336'
                left.markdown(f"""
                  <div class='mover-row'>
                    <img src='{r['Logo']}' width=24 />
                    <span class='mover-name'>{r['name']} ({r['Symbol']})</span>
                    <span style='margin-left:auto;color:{clr};font-weight:bold'>{p:+.2f}%</span>
                  </div>
                """, unsafe_allow_html=True)
        with right:
            st.markdown(f"**Top Losers ({timeframe})**")
            for _, r in bot5.iterrows():
                p = r[pct_col]; clr = '#4CAF50' if p>=0 else '#F44336'
                right.markdown(f"""
                  <div class='mover-row'>
                    <img src='{r['Logo']}' width=24 />
                    <span class='mover-name'>{r['name']} ({r['Symbol']})</span>
                    <span style='margin-left:auto;color:{clr};font-weight:bold'>{p:+.2f}%</span>
                  </div>
                """, unsafe_allow_html=True)
        st.markdown("---")

        # All Coins table
        render_coins_table(df, currency)

# ========================
# DETAIL VIEW
# ========================
def display_details():
    cid = st.session_state.selected_coin_id
    sel = df[df['id']==cid]
    if sel.empty:
        st.warning("Coin not found.")
        st.session_state.selected_coin_id = None
        st.rerun()
    coin = sel.iloc[0]

    # Top info bar
    cols = st.columns([0.1,1,0.2,0.2,0.2,0.2,0.2,0.5])
    if coin['Logo']:
        cols[0].image(coin['Logo'], width=40)
    cols[1].markdown(
        f"**<span style='font-size:1.5rem;'>{coin['name']}</span>** "
        f"<span style='color:#AAA'>{coin['Symbol']}</span>",
        unsafe_allow_html=True
    )

    ohlc1 = get_raw_ohlc_data(cid, currency, days=1)
    latest = ohlc1.iloc[-1] if not ohlc1.empty else {}
    pr = coin['current_price']; pc = coin['24h %']
    pc_clr = "change-positive" if pc>=0 else "change-negative"
    cols[2].markdown(
        f"<span class='chart-info-metric'>Price: <span class='chart-info-value'>{pr:,.4f} {currency.upper()}</span></span>",
        unsafe_allow_html=True
    )
    cols[3].markdown(
        f"<span class='chart-info-metric'>24h %: <span class='chart-info-value {pc_clr}'>{pc:+.2f}%</span></span>",
        unsafe_allow_html=True
    )
    for i,k in enumerate(['open','high','low','close'], start=4):
        val = latest.get(k,0.0)
        cols[i].markdown(
            f"<span class='chart-info-metric'>{k.upper()}: <span class='chart-info-value'>{val:,.4f}</span></span>",
            unsafe_allow_html=True
        )
    st.markdown("---")

    # Back + chart controls
    c_back, c_tf, c_ct = st.columns([0.5,3,1])
    if c_back.button("⬅️ Back to Overview"):
        st.session_state.selected_coin_id = None
        st.rerun()

    tf_opts = ['1m','5m','15m','30m','1h','4h','1D','7D','1M','3M','6M','1Y','MAX']
    idx = tf_opts.index('1D')
    sel_tf = c_tf.radio("Timeframe", tf_opts, index=idx, horizontal=True)
    ctype = c_ct.selectbox("Chart Type", ["Candlestick","OHLC","Line"])

    # Prepare chart data
    ohlc_df = pd.DataFrame()
    if sel_tf in ['1m','5m','15m','30m','1h','4h','1D']:
        raw = get_raw_ohlc_data(cid,currency,1)
        if sel_tf in ['1m','1D']:
            ohlc_df = raw
        else:
            m = {'5m':'5min','15m':'15min','30m':'30min','1h':'1H','4h':'4H'}
            ohlc_df = resample_ohlc(raw, m[sel_tf])
    else:
        dm = {'7D':7,'1M':30,'3M':90,'6M':180,'1Y':365,'MAX':365}
        ohlc_df = get_raw_ohlc_data(cid,currency,dm.get(sel_tf,30))

    loaded = False
    if ctype in ["Candlestick","OHLC"] and not ohlc_df.empty:
        if ctype=="Candlestick":
            fig = go.Figure(go.Candlestick(
                x=ohlc_df['date'], open=ohlc_df['open'], high=ohlc_df['high'],
                low=ohlc_df['low'], close=ohlc_df['close'],
                increasing_line_color='#4CAF50', decreasing_line_color='#F44336'
            ))
        else:
            fig = go.Figure(go.Ohlc(
                x=ohlc_df['date'], open=ohlc_df['open'], high=ohlc_df['high'],
                low=ohlc_df['low'], close=ohlc_df['close'],
                increasing_line_color='#4CAF50', decreasing_line_color='#F44336'
            ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="#E0E0E0",
            hovermode="x unified",
            title=f"{coin['name']} {ctype} ({sel_tf})"
        )
        st.plotly_chart(fig, use_container_width=True)
        loaded = True

    elif ctype=="Line":
        dm = {'1m':1,'5m':1,'15m':1,'30m':1,'1h':1,'4h':1,'1D':1,
              '7D':7,'1M':30,'3M':90,'6M':180,'1Y':365,'MAX':365}
        ld = get_historical_data(cid, currency, dm.get(sel_tf,30))
        if not ld.empty:
            fig = px.line(ld, 'date','price', title=f"{coin['name']} Price ({sel_tf})")
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#E0E0E0",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            loaded = True

    if not loaded:
        st.info("No chart data for this selection.")

    st.markdown("---")
    mc, vol = coin['market_cap'], coin['total_volume']
    c1, c2 = st.columns(2)
    c1.metric("Market Cap", format_currency(mc, currency))
    c2.metric("24h Volume", format_currency(vol, currency))
    c1.metric("Rank", f"#{coin['market_cap_rank']}")

# ========================
# MAIN
# ========================
if st.session_state.selected_coin_id:
    display_details()
else:
    display_overview()
