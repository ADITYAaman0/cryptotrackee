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
.central-header {font-family:'Orbitron'; font-size:3.5rem; text-align:center;
  background:linear-gradient(45deg,#4CAF50,#2196F3);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  margin-bottom:20px; text-shadow:2px 2px 4px rgba(0,0,0,0.3);}
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
    _, mid, _ = st.columns([1,3,1])
    with mid:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim: st_lottie(anim, height=200)
        st.markdown("<div class='central-header'>CRYPTO TRACKEE</div>", unsafe_allow_html=True)
    st.markdown("---")

# ========================
# HELPERS & DATA LOADER
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
def get_client(): return CoinGeckoAPI()
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
    df['24h %'] = pd.to_numeric(df.get('price_change_percentage_24h_in_currency'), errors='coerce').fillna(0)
    df['7d %']  = pd.to_numeric(df.get('price_change_percentage_7d_in_currency'), errors='coerce').fillna(0)
    df['30d %'] = pd.to_numeric(df.get('price_change_percentage_30d_in_currency'), errors='coerce').fillna(0)
    df['Symbol'] = df['symbol'].str.upper()
    df['Logo']   = df['image']
    df['current_price']  = pd.to_numeric(df['current_price'], errors='coerce').fillna(0)
    df['market_cap']      = pd.to_numeric(df['market_cap'], errors='coerce').fillna(0)
    df['total_volume']    = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['market_cap_rank'] = pd.to_numeric(df['market_cap_rank'], errors='coerce').fillna(0).astype(int)
    df['7d Sparkline']    = df['sparkline_in_7d'].apply(
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

def resample_ohlc(df_in, interval):
    return (df_in.set_index('date')
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

# ========================
# STATE INIT
# ========================
st.session_state.setdefault('watchlist', [])
st.session_state.setdefault('selected_coin_id', None)
st.session_state.setdefault('search_query', "")

# ========================
# DATA & WATCHLIST
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
# RENDER TABLE
# ========================
def render_coins_table(df_show):
    if df_show.empty:
        st.write("No coins to display."); return
    specs = [0.4,2.2,1.5,0.8,1.8,1.8,0.5]
    headers = ["#","Coin",f"Price ({currency.upper()})","24h %","Market Cap","7d Sparkline","★"]
    cols = st.columns(specs)
    for c,h in zip(cols, headers):
        c.markdown(f"**{h}**")
    for idx,r in df_show.iterrows():
        c0,c1,c2,c3,c4,c5,c6 = st.columns(specs)
        cid = r['id']
        with c6:
            icon="★" if cid in st.session_state.watchlist else "☆"
            if st.button(icon, key=f"star_{cid}_{idx}"):
                toggle_watchlist(cid); st.rerun()
        c0.write(r['market_cap_rank'])
        name=f"{r['name']} ({r['Symbol']})"; logo=r['Logo']
        btn=f"btn_{cid}_{idx}"
        if logo:
            c1.markdown(
                f"<img src='{logo}' width=20 style='vertical-align:middle;margin-right:5px;'/>"
                f"<button style='background:none;border:none;color:#FFF;' onclick=\"document.getElementById('{btn}').click()\">{name}</button>",
                unsafe_allow_html=True
            )
            if c1.button(" ", key=btn, use_container_width=True):
                st.session_state.selected_coin_id=cid; st.session_state.search_query=""; st.rerun()
        else:
            if c1.button(name, key=btn):
                st.session_state.selected_coin_id=cid; st.session_state.search_query=""; st.rerun()
        c2.write(f"{r['current_price']:,.4f}")
        pct, clr = r['24h %'], ('#4CAF50' if r['24h %']>=0 else '#F44336')
        c3.markdown(f"<span style='color:{clr};font-weight:bold'>{pct:+.2f}%</span>",unsafe_allow_html=True)
        c4.write(format_currency(r['market_cap'],currency))
        sp=r['7d Sparkline']
        if sp: c5.image(sp,use_container_width=True)
        else: c5.write("–")
        st.markdown("<hr style='border-color:#333;margin:4px 0;'>",unsafe_allow_html=True)

# ========================
# OVERVIEW / SEARCH / MOVERS
# ========================
def display_overview():
    # Search
    q = st.text_input("🔍 Search Coins", st.session_state.search_query, placeholder="Name or symbol")
    if q != st.session_state.search_query:
        st.session_state.search_query = q; st.rerun()

    # Key Metrics
    st.subheader("Key Metrics")
    bcol, ecol, _ = st.columns([1,1,2])
    for sym, col in [('BTC',bcol),('ETH',ecol)]:
        sel=df[df['Symbol']==sym]
        if not sel.empty:
            pr, ch = sel.iloc[0]['current_price'], sel.iloc[0]['24h %']
            col.metric(f"{sym} Price", f"{pr:,.2f} {currency.upper()}", f"{ch:+.2f}%")
        else:
            col.metric(f"{sym} Price", "N/A","N/A")

    # —— Styled Top 5 Gainers & Top 5 Losers —— #
    st.subheader(f"📊 Top 5 Gainers & Losers ({timeframe})")
    pct_col = {'24h':'24h %','7d':'7d %','30d':'30d %'}[timeframe]

    gainers_df = df.nlargest(5,pct_col)[
        ['market_cap_rank','name','Symbol','current_price',pct_col,'market_cap']
    ].rename(columns={
        'market_cap_rank':'Rank','name':'Name','Symbol':'Symbol',
        'current_price':f'Price ({currency.upper()})',
        pct_col:f'{timeframe} %','market_cap':'Market Cap'
    })
    losers_df = df.nsmallest(5,pct_col)[
        ['market_cap_rank','name','Symbol','current_price',pct_col,'market_cap']
    ].rename(columns={
        'market_cap_rank':'Rank','name':'Name','Symbol':'Symbol',
        'current_price':f'Price ({currency.upper()})',
        pct_col:f'{timeframe} %','market_cap':'Market Cap'
    })

    def color_pct(v): return f"color: {'#4CAF50' if v>=0 else '#F44336'}; font-weight:bold;"
    def fmt_mc(x): return format_currency(x,currency)

    styled_g = (gainers_df.style
        .format({f'Price ({currency.upper()})':'${:,.4f}',
                 f'{timeframe} %':'{:+.2f}%',
                 'Market Cap':fmt_mc})
        .applymap(color_pct, subset=[f'{timeframe} %'])
        .set_properties(**{'background-color':'#1A1A1A','color':'#E0E0E0','border':'1px solid #333'})
        .set_table_styles([{'selector':'th','props':[('background-color','#333'),('color','#FFF'),('font-family','Kanit')]},
                           {'selector':'td','props':[('font-family','Kanit')]}])
    )
    styled_l = (losers_df.style
        .format({f'Price ({currency.upper()})':'${:,.4f}',
                 f'{timeframe} %':'{:+.2f}%',
                 'Market Cap':fmt_mc})
        .applymap(color_pct, subset=[f'{timeframe} %'])
        .set_properties(**{'background-color':'#1A1A1A','color':'#E0E0E0','border':'1px solid #333'})
        .set_table_styles([{'selector':'th','props':[('background-color','#333'),('color','#FFF'),('font-family','Kanit')]},
                           {'selector':'td','props':[('font-family','Kanit')]}])
    )

    gcol, lcol = st.columns(2)
    with gcol:
        st.write("🔥 Top 5 Gainers")
        st.dataframe(styled_g, use_container_width=True)
    with lcol:
        st.write("❄️ Top 5 Losers")
        st.dataframe(styled_l, use_container_width=True)

    st.markdown("---")
    # —— end styled tables —— #

    # Full coins table or search results
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
    # ... your existing detail-view code ...
    pass

# ========================
# MAIN
# ========================
if st.session_state.selected_coin_id:
    display_details()
else:
    display_overview()
