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
    fig.write_image(buf, format='png', engine='kaleido') # Ensure Kaleido is installed or use another engine
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

@st.cache_data(ttl=60)
def load_data(vs_currency: str):
    data = cg.get_coins_markets(
        vs_currency=vs_currency, order="market_cap_desc", per_page=250,
        sparkline=True, price_change_percentage="24h,7d,30d"
    )
    df = pd.DataFrame(data)
    if not df.empty:
        df["24h %"]  = df["price_change_percentage_24h_in_currency"].fillna(0)
        df["7d %"]   = df["price_change_percentage_7d_in_currency"].fillna(0)
        df["30d %"]  = df["price_change_percentage_30d_in_currency"].fillna(0)
        df["Symbol"] = df["symbol"].str.upper()
        df["Logo"]   = df["image"]
        if "sparkline_in_7d" in df.columns:
             df["7d Spark"] = df["sparkline_in_7d"].apply(lambda x: create_spark(x["price"]) if x and "price" in x else "")
        else:
            df["7d Spark"] = ""
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
    supported_currencies = cg.get_supported_vs_currencies()
    if supported_currencies:
        currency = st.selectbox("Currency", sorted(supported_currencies), index=sorted(supported_currencies).index("usd") if "usd" in supported_currencies else 0)
    else:
        st.error("Failed to load supported currencies.")
        currency = "usd" # Fallback
        
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
    current_search = st.text_input(
        "🔍 Search Coins (filters only Overview)",
        placeholder="Name or symbol…",
        value=st.session_state.search, # Use value for controlled component
        key="search_input_key" # Unique key for text_input
    )
    if current_search != st.session_state.search: # Update search state if input changes
        st.session_state.search = current_search
        st.experimental_rerun()


    if st.button("🔙 Clear Search"):
        st.session_state.search = ""
        # Clear the text input as well
        st.session_state.search_input_key = "" # May need a more robust way if text_input doesn't clear
        st.experimental_rerun()
    st.markdown("---")

# ─── LOAD FULL DATA ────────────────────────────────────────────────────────────
df_full = load_data(currency)

# ─── SPLIT FOR OVERVIEW FILTER ─────────────────────────────────────────────────
if st.session_state.search:
    search_term = st.session_state.search.lower()
    mask = (
        df_full["name"].str.lower().str.contains(search_term, na=False) |
        df_full["Symbol"].str.lower().str.contains(search_term, na=False)
    )
    df_overview = df_full[mask]
else:
    df_overview = df_full

# ─── VIEW ─────────────────────────────────────────────────────────────────────
def show_movers(dfm, title, icon, col_name):
    st.markdown(f"**{icon} {title}**")
    if col_name not in dfm.columns:
        st.warning(f"Column '{col_name}' not found for movers.")
        return
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
    st.warning("No data loaded. Check API or currency selection.")
else:
    # DETAIL VIEW
    if st.session_state.selected_coin:
        sel = df_full[df_full["id"]==st.session_state.selected_coin]
        if sel.empty:
            st.session_state.selected_coin = None
            st.experimental_rerun()
        else: # Added else to prevent error if sel is empty
            coin = sel.iloc[0]
            st.subheader(f"{coin['name']} ({coin['Symbol']})")
            if st.button("⬅️ Back"):
                st.session_state.selected_coin = None
                st.experimental_rerun()

            # Chart selector
            ct = st.selectbox("Chart Type", ["Line","Candlestick","OHLC"])
            days = st.slider("History (days)",7,90,30, key=f"days_slider_{coin['id']}") # Unique key
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
                else: # OHLC
                    fig = go.Figure([go.Ohlc(
                        x=ohlc["date"],
                        open=ohlc["open"], high=ohlc["high"],
                        low=ohlc["low"], close=ohlc["close"]
                    )])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", title_font_color="#FFFFFF", font_color="#FFFFFF", yaxis_tickformat = '.8f')
            fig.update_xaxes(showgrid=False, color="#FFFFFF")
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color="#FFFFFF")

            st.plotly_chart(fig, use_container_width=True)

            # Metrics
            st.subheader("Info & Metrics")
            mc1, mc2 = st.columns(2)
            mc1.metric("Price", f"{coin['current_price']:.4f} {currency.upper()}", f"{coin['24h %']:.2f}%")
            mc2.metric("Market Cap", f"${coin['market_cap']:,}" if currency.lower() == 'usd' else f"{coin['market_cap']:,} {currency.upper()}")
            mc1.metric("24h Vol", f"${coin['total_volume']:,}" if currency.lower() == 'usd' else f"{coin['total_volume']:,} {currency.upper()}")
            mc2.metric("Rank", f"#{coin['market_cap_rank']}")

    # OVERVIEW & MOVERS
    else:
        # Key Metrics (full df)
        st.subheader("Key Metrics")
        bcol, ecol, tcol = st.columns(3)
        # BTC
        btc = df_full[df_full["Symbol"]=="BTC"]
        if not btc.empty:
            bcol.metric("BTC Price", f"{btc.iloc[0]['current_price']:.2f} {currency.upper()}", f"{btc.iloc[0]['24h %']:.2f}%")
        else:
            bcol.metric("BTC Price","N/A","—")
        # ETH
        eth = df_full[df_full["Symbol"]=="ETH"]
        if not eth.empty:
            ecol.metric("ETH Price", f"{eth.iloc[0]['current_price']:.2f} {currency.upper()}", f"{eth.iloc[0]['24h %']:.2f}%")
        else:
            ecol.metric("ETH Price","N/A","—")
        # Top Gainer
        if "24h %" in df_full.columns and not df_full.empty:
            top = df_full.loc[df_full["24h %"].idxmax()]
            tcol.metric("Top 24h Gainer", f"{top['name']}", f"{top['24h %']:.2f}%")
        else:
            tcol.metric("Top 24h Gainer", "N/A", "—")
        st.markdown("---")

        # Movers (full df)
        col_map = {"24h":"24h %","7d":"7d %","30d":"30d %"}
        pc = col_map[timeframe]
        gcol, lcol = st.columns(2)
        with gcol:
            if pc in df_full.columns:
                show_movers(df_full.nlargest(10,pc), "🚀 Gainers", "🚀", pc)
            else:
                st.warning(f"Gainers data for {timeframe} not available.")
        with lcol:
            if pc in df_full.columns:
                show_movers(df_full.nsmallest(10,pc), "📉 Losers",  "📉", pc)
            else:
                st.warning(f"Losers data for {timeframe} not available.")
        st.markdown("---")

        # Market Overview (filtered df_overview)
        st.subheader("Market Overview")
        if df_overview.empty:
            st.warning("No coins match your search.")
        else:
            tbl = df_overview.head(50)
            # Corrected line for the SyntaxError:
            # The original line was: headers = ["#","C]()
            # "C]() was an unterminated string. Assuming "Coin" was intended.
            # This variable's direct use is not implemented further as its purpose was unclear.
            _ = ["#", "Coin"] # Original problematic line, now syntactically correct and assigned to _.

            # Columns to display in the overview table
            cols_to_display_keys = [
                'market_cap_rank', 'Logo', 'name', 'Symbol', 
                'current_price', '24h %', 'market_cap', '7d Spark'
            ]
            
            # Filter tbl to only include columns that actually exist from the API response
            actual_cols_in_tbl = [col for col in cols_to_display_keys if col in tbl.columns]
            
            # Define column configurations for a richer display
            column_config = {
                "market_cap_rank": st.column_config.NumberColumn("Rank", format="%d", help="Market Cap Rank"),
                "Logo": st.column_config.ImageColumn("Logo", help="Coin Logo"),
                "name": st.column_config.TextColumn("Name", help="Coin Name"),
                "Symbol": st.column_config.TextColumn("Symbol", help="Coin Symbol"),
                "current_price": st.column_config.NumberColumn(
                    f"Price ({currency.upper()})", 
                    format="%.2f" if currency.lower() in ['usd', 'eur', 'gbp'] else "%.6f", # Adjust precision based on currency
                    help="Current Price"
                ),
                "24h %": st.column_config.NumberColumn(
                    "24h Change", 
                    format="%.2f%%",
                    help="Price change percentage in the last 24 hours"
                ),
                "market_cap": st.column_config.NumberColumn(
                    f"Market Cap ({currency.upper()})",
                    format="%.0f", # Display as a whole number
                    help="Market Capitalization"
                ),
                "7d Spark": st.column_config.ImageColumn("7d Sparkline", help="Price trend over the last 7 days")
            }

            # Filter column_config to only include actual_cols_in_tbl that we want to display
            filtered_column_config = {k: v for k, v in column_config.items() if k in actual_cols_in_tbl}

            # Prepare a DataFrame with only the selected columns for display
            display_df = tbl[actual_cols_in_tbl].copy()

            # Add clickable rows for navigating to detail view
            # This requires a bit more handling if we want to make rows clickable in st.dataframe
            # For simplicity, we'll list coins and users can search to see details.
            # Or, one could add a 'Select' button per row if st.dataframe doesn't support row click event easily.
            # For now, just displaying the data.

            st.dataframe(
                display_df,
                column_config=filtered_column_config,
                use_container_width=True,
                hide_index=True
            )

# Auto-refresh logic (optional, can be intensive)
# if not st.session_state.selected_coin: # Only refresh overview
#     if time.time() - st.session_state.last_refresh > refresh_seconds:
#         st.session_state.last_refresh = time.time()
#         st.experimental_rerun()
