import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.graph_objects as go
import requests
import base64
from io import BytesIO
from streamlit_lottie import st_lottie
import streamlit.components.v1 as components

# ========================
# APP CONFIGURATION & CSS
# ========================
st.set_page_config(page_title="CRYPTO TRACKEE", page_icon="💸", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@400;700&family=Orbitron:wght@500&display=swap');
.central-header { /* ... */ }
.stMetric { /* ... */ }
.mover-row { /* ... */ }
.mover-name { /* ... */ }
.stTextInput input { /* ... */ }
.stButton > button { /* ... */ }
.chart-info-metric { /* ... */ }
.chart-info-value { /* ... */ }
.change-positive {color:#4CAF50;}
.change-negative {color:#F44336;}
</style>
""", unsafe_allow_html=True)

# ========================
# HEADER + LOTTIE
# ========================
def load_lottie(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
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
@st.cache_resource
def get_cg(): return CoinGeckoAPI()
cg = get_cg()

def abbreviate_number(num: float) -> str:
    for unit in ['','K','M','B','T']:
        if abs(num) < 1000:
            return f"{num:.2f}{unit}"
        num /= 1000
    return f"{num:.2f}E"

def format_currency(n, cur):
    s = abbreviate_number(n)
    return f"${s}" if cur=='usd' else f"{s} {cur.upper()}"

def create_sparkline(prices):
    # ... same as before ...
    if not isinstance(prices, list) or len(prices)<2: return ""
    s = pd.to_numeric(pd.Series(prices),errors='coerce').dropna().tolist()
    if len(s)<2: return ""
    fig = go.Figure(go.Scatter(x=list(range(len(s))), y=s, mode='lines',
        line=dict(color='#4CAF50' if s[-1]>=s[0] else '#F44336', width=2)))
    fig.update_layout(... )  # omitted for brevity
    buf = BytesIO(); fig.write_image(buf,format='png',engine='kaleido')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

@st.cache_data(ttl=30)
def load_market_data(cur):
    data = cg.get_coins_markets(vs_currency=cur, order='market_cap_desc',
                                per_page=250, sparkline=True,
                                price_change_percentage='24h,7d,30d')
    df = pd.DataFrame(data)
    # compute % columns, uppercase symbols, etc.
    df['24h %'] = pd.to_numeric(df['price_change_percentage_24h_in_currency'], errors='coerce').fillna(0)
    df['7d %']  = pd.to_numeric(df['price_change_percentage_7d_in_currency'], errors='coerce').fillna(0)
    df['30d %'] = pd.to_numeric(df['price_change_percentage_30d_in_currency'], errors='coerce').fillna(0)
    df['Symbol']= df['symbol'].str.upper()
    df['Logo']  = df['image']
    df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0)
    df['market_cap']     = pd.to_numeric(df['market_cap'], errors='coerce').fillna(0)
    df['total_volume']   = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0)
    df['market_cap_rank']= pd.to_numeric(df['market_cap_rank'], errors='coerce').fillna(0).astype(int)
    df['7d Sparkline']   = df['sparkline_in_7d'].apply(lambda x: create_sparkline(x['price']) if isinstance(x,dict) else "")
    return df

# ========================
# SESSION / SIDEBAR
# ========================
st.session_state.setdefault('watchlist', [])
st.session_state.setdefault('selected_coin', None)
st.session_state.setdefault('search_query', "")

with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    supported = sorted(cg.get_supported_vs_currencies())
    currency  = st.selectbox("Currency", supported, index=supported.index('usd'))
    timeframe = st.selectbox("Movers Timeframe", ['24h','7d','30d'], index=1)
    refresh   = st.slider("Auto-Refresh (s)", 10, 300, 30)

df = load_market_data(currency)

def toggle_wl(cid):
    wl = st.session_state.watchlist
    if cid in wl: wl.remove(cid)
    else:        wl.append(cid)

def display_watchlist():
    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Watchlist")
    if not st.session_state.watchlist:
        st.sidebar.info("Click ★ in the table to add.")
        return
    sub = df[df['id'].isin(st.session_state.watchlist)]
    for _,r in sub.iterrows():
        c1,c2 = st.sidebar.columns([1,4])
        c1.image(r['Logo'], width=32)
        pct,clr = r['24h %'], '#4CAF50' if r['24h %']>=0 else '#F44336'
        c2.markdown(f"**{r['name']}**<br>"
                    f"{r['current_price']:.4f} {currency.upper()} "
                    f"<span style='color:{clr};'>{pct:+.2f}%</span>",
                    unsafe_allow_html=True)

display_watchlist()

# ========================
# TABLE RENDERING
# ========================
def render_table(data):
    specs=[0.3,2.5,1.5,0.8,1.8,1.8,0.5]
    hdrs=["#","Coin",f"Price ({currency.upper()})","24h %","Market Cap","7d Sparkline","★"]
    cols = st.columns(specs)
    for c,h in zip(cols,hdrs): c.markdown(f"**{h}**")
    for i,r in data.iterrows():
        c0,c1,c2,c3,c4,c5,c6 = st.columns(specs)
        cid=r['id']
        with c6:
            icon="★" if cid in st.session_state.watchlist else "☆"
            if st.button(icon, key=f"star_{i}"):
                toggle_wl(cid); st.rerun()
        c0.write(r['market_cap_rank'])
        name=f"{r['name']} ({r['Symbol']})"
        btn=f"btn_{i}"
        if r['Logo']:
            c1.markdown(f"<img src='{r['Logo']}' width=20/> "
                        f"<button style='background:none;border:none;color:#FFF;' "
                        f"onclick=\"document.getElementById('{btn}').click()\">{name}</button>",
                        unsafe_allow_html=True)
            if c1.button(" ",key=btn,use_container_width=True):
                st.session_state.selected_coin=cid; st.session_state.search_query=""; st.rerun()
        else:
            if c1.button(name,key=btn):
                st.session_state.selected_coin=cid; st.session_state.search_query=""; st.rerun()
        c2.write(f"{r['current_price']:.4f}")
        pct,clr=r['24h %'], '#4CAF50' if pct>=0 else '#F44336'
        c3.markdown(f"<span style='color:{clr};font-weight:bold'>{pct:+.2f}%</span>",unsafe_allow_html=True)
        c4.write(format_currency(r['market_cap'],currency))
        if r['7d Sparkline']:
            c5.image(r['7d Sparkline'],use_container_width=True)
        else:
            c5.write("–")
        st.markdown("<hr style='margin:4px 0; border-color:#333;'>", unsafe_allow_html=True)

# ========================
# OVERVIEW
# ========================
def display_overview():
    q = st.text_input("🔍 Search", st.session_state.search_query)
    if q!=st.session_state.search_query:
        st.session_state.search_query=q; st.rerun()

    # Key metrics
    st.subheader("Key Metrics")
    bcol,ecol,_ = st.columns([1,1,2])
    for sym,col in [('BTC',bcol),('ETH',ecol)]:
        sel = df[df['Symbol']==sym]
        if not sel.empty:
            p,c=sel.iloc[0]['current_price'],sel.iloc[0]['24h %']
            col.metric(f"{sym} Price",f"{p:.2f} {currency.upper()}",f"{c:+.2f}%")
        else:
            col.metric(f"{sym} Price","N/A","N/A")

    # Styled Gainers/Losers
    st.subheader(f"Top 5 Gainers & Losers ({timeframe})")
    pctcol={'24h':'24h %','7d':'7d %','30d':'30d %'}[timeframe]
    g5 = df.nlargest(5,pctcol)[['name','Symbol',pctcol]].set_index('name')
    l5 = df.nsmallest(5,pctcol)[['name','Symbol',pctcol]].set_index('name')
    def highlight(s): return ['color:green' if v>=0 else 'color:red' for v in s]
    gtable = g5.style.format({pctcol:'{:+.2f}%'}).apply(highlight,subset=[pctcol])
    ltable = l5.style.format({pctcol:'{:+.2f}%'}).apply(highlight,subset=[pctcol])
    gcol,lcol=st.columns(2)
    with gcol:
        st.write("🔥 Gainers"); st.dataframe(gtable,use_container_width=True)
    with lcol:
        st.write("❄️ Losers");   st.dataframe(ltable,use_container_width=True)
    st.markdown("---")

    # Table
    if st.session_state.search_query:
        mask = df['name'].str.contains(q,case=False)|df['Symbol'].str.contains(q,case=False)
        render_table(df[mask])
    else:
        render_table(df)

# ========================
# DETAIL VIEW + TRADINGVIEW
# ========================
def display_details():
    cid = st.session_state.selected_coin
    sel = df[df['id']==cid]
    if sel.empty:
        st.session_state.selected_coin=None; st.rerun()
    coin=sel.iloc[0]

    st.subheader(f"{coin['name']} ({coin['Symbol']})")
    # Plotly multi-panel omitted for brevity...
    # ——————————————
    # TradingView widget embed:
    symbol_input = st.text_input("TV Widget Symbol", f"BINANCE:{coin['Symbol']}USDT")
    interval_input = st.selectbox("Interval", ["1","5","15","60","D","W","M"])
    theme_input = st.selectbox("Theme",["dark","light"])
    # load our tv_widget.html template:
    with open("tv_widget.html") as f:
        tv_html = f.read()
    tv_html = tv_html.replace('symbol: "BINANCE:BTCUSDT"', f'symbol: "{symbol_input}"')
    tv_html = tv_html.replace('interval: "60"',         f'interval: "{interval_input}"')
    if theme_input=="light":
        tv_html = tv_html.replace('"paneProperties.background": "#0A0A1A"',
                                  '"paneProperties.background": "#FFFFFF"')
    components.html(tv_html, height=700, scrolling=True)

# ========================
# MAIN
# ========================
if st.session_state.selected_coin:
    display_details()
else:
    display_overview()
