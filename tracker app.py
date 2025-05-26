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
    # Make sure you have kaleido installed: pip install kaleido
    fig.write_image(buf, format='png', engine='kaleido')
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

@st.cache_data(ttl=60)
def load_data(vs_currency: str):
    data = cg.get_coins_markets(
        vs_currency=vs_currency, order="market_cap_desc", per_page=250,
        sparkline=True, price_change_percentage="24h,7d,30d"
    )
    df = pd.DataFrame(data)
    # Add checks for column existence before trying to use them
    if not df.empty:
        df["24h %"]  = df["price_change_percentage_24h_in_currency"].fillna(0) if "price_change_percentage_24h_in_currency" in df.columns else 0
        df["7d %"]   = df["price_change_percentage_7d_in_currency"].fillna(0) if "price_change_percentage_7d_in_currency" in df.columns else 0
        df["30d %"]  = df["price_change_percentage_30d_in_currency"].fillna(0) if "price_change_percentage_30d_in_currency" in df.columns else 0
        df["Symbol"] = df["symbol"].str.upper() if "symbol" in df.columns else ""
        df["Logo"]   = df["image"] if "image" in df.columns else ""
        if "sparkline_in_7d" in df.columns and df["sparkline_in_7d"].apply(lambda x: isinstance(x, dict) and "price" in x).all():
            df["7d Spark"] = df["sparkline_in_7d"].apply(lambda x: create_spark(x["price"]))
        else:
            df["7d Spark"] = "" # Placeholder if data is missing or malformed
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
    supported = []
    try:
        supported = sorted(cg.get_supported_vs_currencies())
    except Exception as e:
        st.error(f"Could not fetch supported currencies: {e}")

    if supported:
        default_currency_index = supported.index("usd") if "usd" in supported else 0
        currency = st.selectbox("Currency", supported, index=default_currency_index)
    else:
        currency = st.text_input("Currency", value="usd") # Fallback if API fails
        st.warning("Could not load currency list. Defaulting to USD. You can type another if needed.")

    timeframe = st.selectbox("Movers Timeframe", ["24h","7d","30d"], index=1)
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
    
    # Ensure st.session_state.search is used for the input's value to persist
    search_value = st.text_input(
        "🔍 Search Coins (filters only Overview)",
        placeholder="Name or symbol…",
        value=st.session_state.search, # Control the input with session state
        key="search_input_field" # Give a unique key
    )
    if search_value != st.session_state.search:
        st.session_state.search = search_value
        st.experimental_rerun() # Rerun if search term changes

    if st.button("🔙 Clear Search"):
        st.session_state.search = ""
        # To clear the text_input widget itself, we need to manage its value via session_state
        # and rerun. The above line already does this effectively by setting search to ""
        st.experimental_rerun()
    st.markdown("---")

# ─── LOAD FULL DATA ────────────────────────────────────────────────────────────
df_full = load_data(currency)

# ─── SPLIT FOR OVERVIEW FILTER ─────────────────────────────────────────────────
if st.session_state.search and not df_full.empty: # Add check for df_full not empty
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
    # Ensure the column exists to prevent KeyErrors
    if col_name not in dfm.columns:
        st.warning(f"Data for '{col_name}' not available for movers display.")
        return
    for _, row in dfm.iterrows():
        pct = row[col_name]
        clr = "#4CAF50" if pct>=0 else "#F44336"
        st.markdown(
            f"<div style='display:flex;align-items:center'>"
            f"<img src='{row.get('Logo', '')}' width=24>" # Use .get for safety
            f"<span style='margin-left:8px'>{row.get('name', 'N/A')}</span>"
            f"<span style='margin-left:auto;color:{clr};font-weight:bold'>{pct:+.2f}%</span>"
            f"</div>",
            unsafe_allow_html=True
        )

# Main rendering
if df_full.empty:
    st.warning("No data loaded. Please check your internet connection or API compatibility.")
else:
    # DETAIL VIEW
    if st.session_state.selected_coin:
        sel = df_full[df_full["id"]==st.session_state.selected_coin]
        if sel.empty:
            st.session_state.selected_coin = None
            st.experimental_rerun()
        else: # ensure coin is only accessed if sel is not empty
            coin = sel.iloc[0]
            st.subheader(f"{coin.get('name', 'N/A')} ({coin.get('Symbol', 'N/A')})")
            if st.button("⬅️ Back"):
                st.session_state.selected_coin = None
                st.experimental_rerun()

            # Chart selector
            # Add unique keys to widgets if they might be re-rendered with different defaults
            ct = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"], key=f"chart_type_{coin.get('id')}")
            days = st.slider("History (days)",7,90,30, key=f"days_slider_{coin.get('id')}")
            
            fig_title = f"{coin.get('name', 'N/A')} Price ({days}d)"
            try:
                if ct=="Line":
                    hist = get_hist(coin["id"], currency, days)
                    fig = px.line(hist, x="date", y="price", title=fig_title)
                else:
                    ohlc = get_ohlc(coin["id"], currency, days)
                    if ct=="Candlestick":
                        fig = go.Figure([go.Candlestick(
                            x=ohlc["date"],
                            open=ohlc["open"], high=ohlc["high"],
                            low=ohlc["low"], close=ohlc["close"]
                        )])
                    else: # OHLC
                        fig = go.Figure([go.Ohlc(
                            x=ohlc["date"],
                            open=ohlc["open"], high=ohlc["high"],
                            low=ohlc["low"], close=ohlc["close"]
                        )])
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", # Added plot_bgcolor for consistency
                    title_font_color="#FFFFFF",
                    font_color="#FFFFFF"
                )
                fig.update_xaxes(showgrid=False, color="#FFFFFF")
                fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#FFFFFF")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Could not load chart data for {coin.get('name', 'N/A')}: {e}")


            # Metrics
            st.subheader("Info & Metrics")
            mc1, mc2 = st.columns(2)
            mc1.metric("Price", f"{coin.get('current_price', 0):.4f} {currency.upper()}", f"{coin.get('24h %', 0):.2f}%")
            
            market_cap_val = coin.get('market_cap', 0)
            total_volume_val = coin.get('total_volume', 0)
            
            mc2.metric("Market Cap", f"${market_cap_val:,}" if currency.lower() == 'usd' else f"{market_cap_val:,} {currency.upper()}")
            mc1.metric("24h Vol", f"${total_volume_val:,}" if currency.lower() == 'usd' else f"{total_volume_val:,} {currency.upper()}")
            mc2.metric("Rank", f"#{coin.get('market_cap_rank', 'N/A')}")

    # OVERVIEW & MOVERS
    else:
        # Key Metrics (full df)
        st.subheader("Key Metrics")
        bcol, ecol, tcol = st.columns(3)
        
        # BTC
        btc = df_full[df_full["Symbol"]=="BTC"] if "Symbol" in df_full.columns else pd.DataFrame()
        if not btc.empty:
            bcol.metric("BTC", f"{btc.iloc[0].get('current_price', 0):.2f} {currency.upper()}", f"{btc.iloc[0].get('24h %', 0):.2f}%")
        else:
            bcol.metric("BTC","N/A","—")
        
        # ETH
        eth = df_full[df_full["Symbol"]=="ETH"] if "Symbol" in df_full.columns else pd.DataFrame()
        if not eth.empty:
            ecol.metric("ETH", f"{eth.iloc[0].get('current_price', 0):.2f} {currency.upper()}", f"{eth.iloc[0].get('24h %', 0):.2f}%")
        else:
            ecol.metric("ETH","N/A","—")
        
        # Top Gainer
        if "24h %" in df_full.columns and not df_full.empty and not df_full["24h %"].empty:
            try:
                top_gainer_idx = df_full["24h %"].idxmax()
                top = df_full.loc[top_gainer_idx]
                tcol.metric("Top 24h Gainer", f"{top.get('name', 'N/A')}", f"{top.get('24h %', 0):.2f}%")
            except KeyError: # Handle if idxmax returns an index not in df_full (should not happen with .loc)
                tcol.metric("Top 24h Gainer", "Error", "N/A")
        else:
            tcol.metric("Top 24h Gainer", "N/A", "—")
        st.markdown("---")

        # Movers (full df)
        col_map = {"24h":"24h %","7d":"7d %","30d":"30d %"}
        pc = col_map[timeframe]
        gcol, lcol = st.columns(2)
        
        # Ensure 'pc' column exists before trying to sort or display
        if pc in df_full.columns:
            with gcol:
                show_movers(df_full.nlargest(10,pc), "🚀 Gainers", "🚀", pc)
            with lcol:
                show_movers(df_full.nsmallest(10,pc), "📉 Losers",  "📉", pc)
        else:
            st.warning(f"Data for timeframe '{timeframe}' ('{pc}') not available to show movers.")
        st.markdown("---")

        # Market Overview (filtered df_overview)
        st.subheader("Market Overview")
        if df_overview.empty:
            st.warning("No coins match your search or no data available.")
        else:
            tbl = df_overview.head(50)
            # Corrected line for the SyntaxError:
            headers = ["#", "Coin"] # This line is now syntactically correct.
                                    # Its actual use depends on subsequent code you might have.
            
            # If you intend to display the table `tbl`, you would add something like:
            # st.dataframe(tbl)
            # Or, for more control, select and configure columns:
            cols_to_show = [
                'market_cap_rank', 'Logo', 'name', 'Symbol', 
                'current_price', '24h %', 'market_cap', '7d Spark'
            ]
            # Filter out columns that might be missing from tbl
            existing_cols_in_tbl = [col for col in cols_to_show if col in tbl.columns]
            
            if existing_cols_in_tbl:
                 column_config_overview = {
                    "market_cap_rank": st.column_config.NumberColumn("Rank", format="%d"),
                    "Logo": st.column_config.ImageColumn("Logo"),
                    "name": "Name",
                    "Symbol": "Symbol",
                    "current_price": st.column_config.NumberColumn(f"Price ({currency.upper()})", format="%.2f" if currency.lower() in ['usd','eur','gbp'] else "%.6f"),
                    "24h %": st.column_config.NumberColumn("24h %", format="%.2f%%"),
                    "market_cap": st.column_config.NumberColumn(f"Market Cap ({currency.upper()})",format="%.0f"),
                    "7d Spark": st.column_config.ImageColumn("7d Sparkline")
                }
                 # Ensure column_config only refers to existing columns
                 filtered_column_config_overview = {k: v for k, v in column_config_overview.items() if k in existing_cols_in_tbl}

                 st.dataframe(
                    tbl[existing_cols_in_tbl],
                    column_config=filtered_column_config_overview,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Not enough data columns to display the market overview table.")

#Optional: Auto-refresh logic based on sidebar slider (uncomment to enable)
current_time = time.time()
 if not st.session_state.selected_coin: # Only auto-refresh if not in detail view
   if current_time - st.session_state.last_refresh > refresh_seconds:
       st.session_state.last_refresh = current_time
       st.experimental_rerun()
