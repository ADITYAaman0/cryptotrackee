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
    initial_sidebar_state="expanded",
)

# ========================
# CUSTOM STYLING
# ========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@400;700&family=Orbitron:wght@500&display=swap');
.central-header {
  font-family:'Orbitron'; font-size:3.5rem; text-align:center;
  background:linear-gradient(45deg,#4CAF50,#2196F3);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  margin-bottom:20px; text-shadow:2px 2px 4px rgba(0,0,0,0.3);
}
.stMetric {background:#262730;border-radius:12px;padding:20px;
  border:1px solid #4CAF50;box-shadow:0 4px 8px rgba(76,175,80,0.2);}
.mover-row {display:flex;align-items:center;margin-bottom:4px;}
.mover-name {font-family:'Kanit';font-weight:bold;margin-left:8px;color:#FFF;}
.stTextInput > div > div > input {
  border-radius:25px;border:2px solid #4CAF50;padding:10px 15px;
  box-shadow:0 4px 8px rgba(0,0,0,0.2);transition:0.3s;
  color:#E0E0E0;background:#1A1A1A;
}
.stTextInput > div > div > input:focus {
  border-color:#2196F3;box-shadow:0 4px 12px rgba(33,150,243,0.3);
}
.stTextInput label {font-weight:bold;color:#E0E0E0;font-size:1.1rem;
  margin-bottom:5px;display:block;}
.stButton > button {
  border-radius:8px;border:1px solid #F44336;background:#F44336;
  color:#FFF;padding:8px 15px;font-weight:bold;transition:0.2s;
}
.stButton > button:hover {background:#D32F2F;border-color:#D32F2F;}
.chart-info-metric {font-size:1.1rem;color:#E0E0E0;
  margin-right:15px;display:inline-block;}
.chart-info-value {font-weight:bold;}
.change-positive {color:#4CAF50;}
.change-negative {color:#F44336;}
</style>
""", unsafe_allow_html=True)

# ========================
# HEADER WITH LOTTIE
# ========================
def load_lottie(url):
    try:
        r = requests.get(url, timeout=10); r.raise_for_status()
        return r.json()
    except:
        return None

with st.container():
    c1, c2, c3 = st.columns([1,3,1])
    with c2:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim: st_lottie(anim, height=200)
        st.markdown("<div class='central-header'>CRYPTO TRACKEE</div>", unsafe_allow_html=True)
    st.markdown("---")

# ========================
# HELPERS
# ========================
def abbreviate_number(num: float) -> str:
    for unit in ['', 'K', 'M', 'B', 'T']:
        if abs(num) < 1000:
            return f"{num:.2f}{unit}"
        num /= 1000
    return f"{num:.2f}E"

def format_currency(num: float, currency: str) -> str:
    abbr = abbreviate_number(num)
    return f"${abbr}" if currency.lower()=='usd' else f"{abbr} {currency.upper()}"

@st.cache_resource
def get_client():
    return CoinGeckoAPI()
cg = get_client()

def create_sparkline(data):
    if not isinstance(data, list) or len(data)<2: return ""
    s = pd.to_numeric(pd.Series(data), errors='coerce').dropna().tolist()
    if len(s)<2: return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(s))), y=s, mode='lines',
        line=dict(color='#4CAF50' if s[-1]>=s[0] else '#F44336', width=2)
    ))
    fig.update_layout(
        showlegend=False,
        xaxis_visible=False, yaxis_visible=False,
        margin=dict(t=0,b=0,l=0,r=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        width=150, height=50
    )
    buf = BytesIO(); fig.write_image(buf, format='png', engine='kaleido')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

@st.cache_data(ttl=30)
def load_market_data(vs_currency: str) -> pd.DataFrame:
    data = cg.get_coins_markets(
        vs_currency=vs_currency, order='market_cap_desc',
        per_page=250, sparkline=True,
        price_change_percentage='24h,7d,30d'
    )
    df = pd.DataFrame(data)
    df['24h %']  = pd.to_numeric(df.get('price_change_percentage_24h_in_currency'), errors='coerce').fillna(0)
    df['7d %']   = pd.to_numeric(df.get('price_change_percentage_7d_in_currency'), errors='coerce').fillna(0)
    df['30d %']  = pd.to_numeric(df.get('price_change_percentage_30d_in_currency'), errors='coerce').fillna(0)
    df['Symbol']= df['symbol'].str.upper()
    df['Logo']  = df['image']
    df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0)
    df['market_cap']     = pd.to_numeric(df['market_cap'], errors='coerce').fillna(0)
    df['total_volume']   = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['market_cap_rank']= pd.to_numeric(df['market_cap_rank'], errors='coerce').fillna(0).astype(int)
    df['7d Sparkline']   = df['sparkline_in_7d'].apply(
        lambda x: create_sparkline(x['price']) if isinstance(x, dict) and 'price' in x else ""
    )
    return df

@st.cache_data(ttl=3600)
def get_historical_data(cid, vs_currency, days=30):
    chart = cg.get_coin_market_chart_by_id(id=cid, vs_currency=vs_currency, days=days)
    df = pd.DataFrame(chart.get('prices', []), columns=['timestamp','price'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['date','price']].dropna()

@st.cache_data(ttl=60)
def get_raw_ohlc_data(cid, vs_currency, days):
    arr = cg.get_coin_ohlc_by_id(id=cid, vs_currency=vs_currency, days=days)
    df = pd.DataFrame(arr, columns=['timestamp','open','high','low','close'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open','high','low','close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df[['date','open','high','low','close']].dropna()

def resample_ohlc(df, interval):
    return (df.set_index('date')
              .resample(interval)
              .apply({'open':'first','high':'max','low':'min','close':'last'})
              .dropna()
              .reset_index())

# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    supported = sorted(cg.get_supported_vs_currencies())
    currency = st.selectbox("Currency", supported, index=supported.index('usd') if 'usd' in supported else 0)
    timeframe = st.selectbox("Movers Timeframe", ['24h','7d','30d'], index=1)
    refresh_interval = st.slider("Auto-Refresh Interval (s)", 10, 300, 30)
    init_watchlist = lambda: st.session_state.setdefault('watchlist', [])
    init_watchlist()

# ========================
# STATE
# ========================
st.session_state.setdefault('selected_coin_id', None)
st.session_state.setdefault('search_query', "")

# ========================
# LOAD & WATCHLIST
# ========================
df = load_market_data(currency)
def toggle_watchlist(cid):
    wl = st.session_state.watchlist
    if cid in wl: wl.remove(cid)
    else: wl.append(cid)

def display_watchlist():
    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Your Watchlist")
    if not st.session_state.watchlist:
        st.sidebar.info("Add coins to your watchlist ★")
        return
    sub = df[df['id'].isin(st.session_state.watchlist)]
    for _, r in sub.iterrows():
        c1, c2 = st.sidebar.columns([1,4])
        with c1: st.image(r['Logo'], width=40)
        pct, clr = r['24h %'], ('#4CAF50' if r['24h %']>=0 else '#F44336')
        c2.markdown(f"<div style='background:rgba(76,175,80,0.15);padding:8px;border-radius:8px;'>"
                    f"<strong style='color:#FFF;'>{r['name']}</strong><br>"
                    f"{r['current_price']:,.4f} {currency.upper()} "
                    f"<span style='color:{clr};font-weight:bold'>{pct:+.2f}%</span>"
                    "</div>", unsafe_allow_html=True)
display_watchlist()

# ========================
# TABLE RENDERER
# ========================
def render_coins_table(df_show):
    if df_show.empty:
        st.write("No coins to display.")
        return
    specs = [0.4,2.2,1.5,0.8,1.8,1.8,0.5]
    headers = ["#","Coin",f"Price ({currency.upper()})","24h %","Market Cap","7d Sparkline","★"]
    cols = st.columns(specs)
    for c,h in zip(cols, headers):
        c.markdown(f"**{h}**")
    for idx, r in df_show.iterrows():
        c0,c1,c2,c3,c4,c5,c6 = st.columns(specs)
        cid = r['id']
        with c6:
            icon = "★" if cid in st.session_state.watchlist else "☆"
            if st.button(icon, key=f"star_{cid}_{idx}"):
                toggle_watchlist(cid); st.rerun()
        c0.write(r['market_cap_rank'])
        name = f"{r['name']} ({r['Symbol']})"; logo = r['Logo']
        btn = f"btn_{cid}_{idx}"
        if logo:
            c1.markdown(
                f"<img src='{logo}' width=20 style='vertical-align:middle;margin-right:5px;'/>"
                f"<button style='background:none;border:none;color:#FFF;' onclick=\"document.getElementById('{btn}').click()\">{name}</button>",
                unsafe_allow_html=True
            )
            if c1.button(" ", key=btn, use_container_width=True):
                st.session_state.selected_coin_id = cid
                st.session_state.search_query = ""
                st.rerun()
        else:
            if c1.button(name, key=btn):
                st.session_state.selected_coin_id = cid
                st.session_state.search_query = ""
                st.rerun()
        c2.write(f"{r['current_price']:,.4f}")
        pct, clr = r['24h %'], ('#4CAF50' if r['24h %']>=0 else '#F44336')
        c3.markdown(f"<span style='color:{clr};font-weight:bold'>{pct:+.2f}%</span>", unsafe_allow_html=True)
        c4.write(format_currency(r['market_cap'], currency))
        spark = r['7d Sparkline']
        if spark: c5.image(spark, use_container_width=True)
        else: c5.write("–")
        st.markdown("<hr style='border-color:#333;margin:4px 0;'>", unsafe_allow_html=True)

# ========================
# OVERVIEW + MOVERS + SEARCH
# ========================
def display_overview():
    # Search
    q = st.text_input("🔍 Search Coins", st.session_state.search_query, placeholder="Name or symbol")
    if q != st.session_state.search_query:
        st.session_state.search_query = q; st.rerun()

    # Key metrics
    st.subheader("Key Metrics")
    bcol, ecol, _ = st.columns([1,1,2])
    for sym, col in [('BTC', bcol), ('ETH', ecol)]:
        sel = df[df['Symbol']==sym]
        if not sel.empty:
            pr, ch = sel.iloc[0]['current_price'], sel.iloc[0]['24h %']
            col.metric(f"{sym} Price", f"{pr:,.2f} {currency.upper()}", f"{ch:+.2f}%")
        else:
            col.metric(f"{sym} Price", "N/A", "N/A")

    # Top Gainers / Losers
    st.subheader(f"Top Gainers & Top Losers ({timeframe})")
    pct_col = {'24h':'24h %','7d':'7d %','30d':'30d %'}[timeframe]
    gainers = df.nlargest(5, pct_col)
    losers  = df.nsmallest(5, pct_col)
    left, right = st.columns(2)
    with left:
        st.markdown("**Gainers**")
        for _, r in gainers.iterrows():
            p, c = r[pct_col], ('#4CAF50' if r[pct_col]>=0 else '#F44336')
            left.markdown(f"<div class='mover-row'>"
                          f"<img src='{r['Logo']}' width=24/>"
                          f"<span class='mover-name'>{r['name']} ({r['Symbol']})</span>"
                          f"<span style='margin-left:auto;color:{c};font-weight:bold'>{p:+.2f}%</span>"
                          f"</div>", unsafe_allow_html=True)
    with right:
        st.markdown("**Losers**")
        for _, r in losers.iterrows():
            p, c = r[pct_col], ('#4CAF50' if r[pct_col]>=0 else '#F44336')
            right.markdown(f"<div class='mover-row'>"
                           f"<img src='{r['Logo']}' width=24/>"
                           f"<span class='mover-name'>{r['name']} ({r['Symbol']})</span>"
                           f"<span style='margin-left:auto;color:{c};font-weight:bold'>{p:+.2f}%</span>"
                           f"</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Table
    if st.session_state.search_query.strip():
        st.subheader(f"Search Results for “{st.session_state.search_query}”")
        mask = df['name'].str.lower().str.contains(q.lower()) | df['Symbol'].str.lower().str.contains(q.lower())
        render_coins_table(df[mask])
    else:
        st.subheader("All Coins")
        render_coins_table(df)

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
    # Info bar
    cols = st.columns([0.1,1,0.2,0.2,0.2,0.2,0.2,0.5])
    if coin['Logo']: cols[0].image(coin['Logo'], width=40)
    cols[1].markdown(
        f"**<span style='font-size:1.5rem;'>{coin['name']}</span>** "
        f"<span style='color:#AAA'>{coin['Symbol']}</span>",
        unsafe_allow_html=True
    )
    ohlc1 = get_raw_ohlc_data(cid, currency, 1)
    latest = ohlc1.iloc[-1] if not ohlc1.empty else {}
    pr, pc = coin['current_price'], coin['24h %']
    pc_cls = "change-positive" if pc>=0 else "change-negative"
    cols[2].markdown(
        f"<span class='chart-info-metric'>Price: <span class='chart-info-value'>{pr:,.4f} {currency.upper()}</span></span>",
        unsafe_allow_html=True
    )
    cols[3].markdown(
        f"<span class='chart-info-metric'>24h %: <span class='chart-info-value {pc_cls}'>{pc:+.2f}%</span></span>",
        unsafe_allow_html=True
    )
    for i,k in enumerate(['open','high','low','close'], start=4):
        val = latest.get(k,0.0)
        cols[i].markdown(
            f"<span class='chart-info-metric'>{k.upper()}: <span class='chart-info-value'>{val:,.4f}</span></span>",
            unsafe_allow_html=True
        )
    st.markdown("---")
    # Back + controls
    back, tf_col, type_col = st.columns([0.5,3,1])
    if back.button("⬅️ Back to Overview"):
        st.session_state.selected_coin_id = None; st.rerun()
    tf_opts = ['1m','5m','15m','30m','1h','4h','1D','7D','1M','3M','6M','1Y','MAX']
    idx = tf_opts.index('1D')
    sel_tf = tf_col.radio("Timeframe", tf_opts, index=idx, horizontal=True)
    ctype = type_col.selectbox("Chart Type", ["Candlestick","OHLC","Line"])
    # fetch chart data
    df_chart = pd.DataFrame()
    if sel_tf in ['1m','5m','15m','30m','1h','4h','1D']:
        raw = get_raw_ohlc_data(cid, currency, 1)
        if sel_tf in ['1m','1D']:
            df_chart = raw
        else:
            mp = {'5m':'5min','15m':'15min','30m':'30min','1h':'1H','4h':'4H'}
            df_chart = resample_ohlc(raw, mp[sel_tf])
    else:
        days_map = {'7D':7,'1M':30,'3M':90,'6M':180,'1Y':365,'MAX':365}
        df_chart = get_raw_ohlc_data(cid, currency, days_map[sel_tf])
    plotted = False
    if ctype in ["Candlestick","OHLC"] and not df_chart.empty:
        if ctype=="Candlestick":
            fig = go.Figure(go.Candlestick(
                x=df_chart['date'], open=df_chart['open'], high=df_chart['high'],
                low=df_chart['low'], close=df_chart['close'],
                increasing_line_color='#4CAF50', decreasing_line_color='#F44336'
            ))
        else:
            fig = go.Figure(go.Ohlc(
                x=df_chart['date'], open=df_chart['open'], high=df_chart['high'],
                low=df_chart['low'], close=df_chart['close'],
                increasing_line_color='#4CAF50', decreasing_line_color='#F44336'
            ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="#E0E0E0", hovermode="x unified",
            title=f"{coin['name']} {ctype} ({sel_tf})"
        )
        st.plotly_chart(fig, use_container_width=True); plotted = True
    elif ctype=="Line":
        days_map = {'1m':1,'5m':1,'15m':1,'30m':1,'1h':1,'4h':1,'1D':1,'7D':7,
                    '1M':30,'3M':90,'6M':180,'1Y':365,'MAX':365}
        ld = get_historical_data(cid, currency, days_map[sel_tf])
        if not ld.empty:
            fig = px.line(ld, 'date','price', title=f"{coin['name']} Price ({sel_tf})")
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color="#E0E0E0", hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True); plotted = True
    if not plotted:
        st.info("No data for this chart selection.")
    st.markdown("---")
    mc, vol = coin['market_cap'], coin['total_volume']
    m1, m2 = st.columns(2)
    m1.metric("Market Cap", format_currency(mc, currency))
    m2.metric("24h Volume", format_currency(vol, currency))
    m1.metric("Rank", f"#{coin['market_cap_rank']}")

# ========================
# MAIN
# ========================
if st.session_state.selected_coin_id:
    display_details()
else:
    display_overview()
