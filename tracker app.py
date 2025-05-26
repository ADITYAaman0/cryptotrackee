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

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CRYPTO TRACKEE",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── STYLING & ANIMATION ──────────────────────────────────────────────────────
st.markdown("""
<style>
.central-header {
  font-size:3rem; font-weight:bold;
  text-align:center; color:#FFF;
  margin-bottom:20px;
}
@keyframes glow {
  0%   { box-shadow: 0 0 5px #4CAF50; }
  50%  { box-shadow: 0 0 20px #4CAF50; }
  100% { box-shadow: 0 0 5px #4CAF50; }
}
[data-baseweb="input"] input {
  animation: glow 2s infinite;
  border: 2px solid #4CAF50 !important;
  border-radius: 8px;
  padding: 8px 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def load_lottie(url: str):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None

@st.cache_resource
def get_client():
    return CoinGeckoAPI()

cg = get_client()

def create_spark(data):
    if not data or len(data)<2:
        return ""
    fig = go.Figure(go.Scatter(
        x=list(range(len(data))), y=data, mode='lines',
        line=dict(color='#4CAF50' if data[-1]>=data[0] else '#F44336', width=2)
    ))
    fig.update_layout(
        showlegend=False, xaxis_visible=False, yaxis_visible=False,
        margin=dict(t=0,b=0,l=0,r=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        width=150, height=50
    )
    buf = BytesIO()
    fig.write_image(buf, format='png', engine='kaleido')
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

@st.cache_data(ttl=60)
def load_data(vs_currency: str):
    data = cg.get_coins_markets(
        vs_currency=vs_currency, order="market_cap_desc", per_page=250,
        sparkline=True, price_change_percentage="24h,7d,30d"
    )
    df = pd.DataFrame(data)
    df["24h %"]  = df["price_change_percentage_24h_in_currency"].fillna(0)
    df["7d %"]   = df["price_change_percentage_7d_in_currency"].fillna(0)
    df["30d %"]  = df["price_change_percentage_30d_in_currency"].fillna(0)
    df["Symbol"] = df["symbol"].str.upper()
    df["Logo"]   = df["image"]
    df["7d Spark"] = df["sparkline_in_7d"].apply(lambda x: create_spark(x["price"]))
    return df

@st.cache_data(ttl=3600)
def get_hist(coin_id, vs_currency, days=30):
    chart = cg.get_coin_market_chart_by_id(coin_id, vs_currency, days)
    df = pd.DataFrame(chart["prices"], columns=["ts","price"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms")
    return df[["date","price"]]

@st.cache_data(ttl=3600)
def get_ohlc(coin_id, vs_currency, days=30):
    data = cg.get_coin_ohlc_by_id(coin_id, vs_currency, days)
    df = pd.DataFrame(data, columns=["ts","open","high","low","close"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms")
    return df[["date","open","high","low","close"]]

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://assets.coingecko.com/coins/images/1/large/bitcoin.png", width=100)
    st.header("⚙️ Settings")
    supported = sorted(cg.get_supported_vs_currencies())
    currency        = st.selectbox("Currency", supported, index=supported.index("usd"))
    timeframe       = st.selectbox("Movers Timeframe", ["24h","7d","30d"], index=1)
    refresh_seconds = st.slider("Refresh Interval (s)", 10,300,60)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "search" not in st.session_state:
    st.session_state.search = ""
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = None

# ─── HEADER + SEARCH (Always Visible) ─────────────────────────────────────────
with st.container():
    c1,c2,c3 = st.columns([1,3,1])
    with c2:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim: st_lottie(anim, height=200)
        st.markdown("<p class='central-header'>CRYPTO TRACKEE</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.session_state.search = st.text_input(
        "🔍 Search Coins (filters only Overview)",
        placeholder="Name or symbol…",
        key="search"
    )
    if st.button("🔙 Clear Search"):
        st.session_state.search = ""
        st.experimental_rerun()
    st.markdown("---")

# ─── LOAD FULL DATA ────────────────────────────────────────────────────────────
df_full = load_data(currency)

# ─── SPLIT FOR OVERVIEW FILTER ─────────────────────────────────────────────────
if st.session_state.search:
    mask = (
        df_full["name"].str.contains(st.session_state.search, case=False, na=False) |
        df_full["Symbol"].str.contains(st.session_state.search, case=False, na=False)
    )
    df_overview = df_full[mask]
else:
    df_overview = df_full

# ─── VIEW ─────────────────────────────────────────────────────────────────────
def show_movers(dfm, title, icon, col_name):
    st.markdown(f"**{icon} {title}**")
    for _, row in dfm.iterrows():
        pct = row[col_name]
        clr = "#4CAF50" if pct>=0 else "#F44336"
        st.markdown(
            f"<div style='display:flex;align-items:center'>"
            f"<img src='{row['Logo']}' width=24>"
            f"<span style='margin-left:8px'>{row['name']}</span>"
            f"<span style='margin-left:auto;color:{clr};font-weight:bold'>{pct:+.2f}%</span>"
            f"</div>",
            unsafe_allow_html=True
        )

# Main rendering
if df_full.empty:
    st.warning("No data loaded.")
else:
    # DETAIL VIEW
    if st.session_state.selected_coin:
        sel = df_full[df_full["id"]==st.session_state.selected_coin]
        if sel.empty:
            st.session_state.selected_coin = None
            st.experimental_rerun()
        coin = sel.iloc[0]
        st.subheader(f"{coin['name']} ({coin['Symbol']})")
        if st.button("⬅️ Back"):
            st.session_state.selected_coin = None
            st.experimental_rerun()

        # Chart selector
        ct = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"])
        days = st.slider("History (days)",7,90,30)
        if ct=="Line":
            hist = get_hist(coin["id"], currency, days)
            fig = px.line(hist, x="date", y="price",
                          title=f"{coin['name']} Price ({days}d)")
        else:
            ohlc = get_ohlc(coin["id"], currency, days)
            if ct=="Candlestick":
                fig = go.Figure([go.Candlestick(
                    x=ohlc["date"],
                    open=ohlc["open"], high=ohlc["high"],
                    low=ohlc["low"], close=ohlc["close"]
                )])
            else:
                fig = go.Figure([go.Ohlc(
                    x=ohlc["date"],
                    open=ohlc["open"], high=ohlc["high"],
                    low=ohlc["low"], close=ohlc["close"]
                )])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        # Metrics
        st.subheader("Info & Metrics")
        mc1, mc2 = st.columns(2)
        mc1.metric("Price", f"{coin['current_price']:.4f} {currency.upper()}", f"{coin['24h %']:.2f}%")
        mc2.metric("Market Cap", f"${coin['market_cap']:,}")
        mc1.metric("24h Vol", f"${coin['total_volume']:,}")
        mc2.metric("Rank", f"#{coin['market_cap_rank']}")

    # OVERVIEW & MOVERS
    else:
        # Key Metrics (full df)
        st.subheader("Key Metrics")
        bcol, ecol, tcol = st.columns(3)
        # BTC
        btc = df_full[df_full["Symbol"]=="BTC"]
        if not btc.empty:
            bcol.metric("BTC", f"{btc.iloc[0]['current_price']:.2f}", f"{btc.iloc[0]['24h %']:.2f}%")
        else:
            bcol.metric("BTC","N/A","—")
        # ETH
        eth = df_full[df_full["Symbol"]=="ETH"]
        if not eth.empty:
            ecol.metric("ETH", f"{eth.iloc[0]['current_price']:.2f}", f"{eth.iloc[0]['24h %']:.2f}%")
        else:
            ecol.metric("ETH","N/A","—")
        # Top Gainer
        top = df_full.loc[df_full["24h %"].idxmax()]
        tcol.metric("Top 24h Gainer", f"{top['name']} ({top['24h %']:.2f}%)")
        st.markdown("---")

        # Movers (full df)
        col_map = {"24h":"24h %","7d":"7d %","30d":"30d %"}
        pc = col_map[timeframe]
        gcol, lcol = st.columns(2)
        with gcol:
            show_movers(df_full.nlargest(10,pc), "🚀 Gainers", "🚀", pc)
        with lcol:
            show_movers(df_full.nsmallest(10,pc), "📉 Losers",  "📉", pc)
        st.markdown("---")

        # Market Overview (filtered df_overview)
        st.subheader("Market Overview")
        if df_overview.empty:
            st.warning("No coins match your search.")
        else:
            tbl = df_overview.head(50)
            headers = ["#","C]()
