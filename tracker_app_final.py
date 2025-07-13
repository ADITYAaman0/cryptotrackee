import streamlit as st
import pandas as pd
from pycoingecko import CoinGeckoAPI
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import base64
from io import BytesIO
from streamlit_lottie import st_lottie
import streamlit.components.v1 as components
import numpy as np
import ta
from streamlit_option_menu import option_menu
import json
import os
from datetime import datetime, timedelta
import time

# APP CONFIGURATION & CSS
st.set_page_config(page_title="CRYPTO TRACKEE", page_icon="💸", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Orbitron:wght@400;500;700;900&display=swap');

.main {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    animation: gradientShift 8s ease infinite;
}

@keyframes gradientShift {
    0% { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    25% { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    50% { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    75% { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    100% { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
}

.central-header {
    font-family: 'Orbitron', monospace;
    font-size: 3.5rem;
    font-weight: 900;
    text-align: center;
    background: linear-gradient(45deg, #FFD700, #FF6B35, #F7931E, #FFD700);
    background-size: 400% 400%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientAnimation 3s ease infinite, pulse 2s ease-in-out infinite alternate;
    text-shadow: 0 0 30px rgba(255, 215, 0, 0.5);
    margin: 20px 0;
}

@keyframes gradientAnimation {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes pulse {
    0% { transform: scale(1); }
    100% { transform: scale(1.05); }
}
</style>
""", unsafe_allow_html=True)

# HEADER + LOTTIE
def load_lottie(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

with st.container():
    header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
    
    with header_col2:
        anim = load_lottie("https://lottie.host/7905f328-9844-41d3-83f2-6962a1e67c9c/uB9iS90Y9K.json")
        if anim: 
            st_lottie(anim, height=250, key="main_animation", speed=1.5)
        
        st.markdown("<div class='central-header floating glow'>CRYPTO TRACKEE</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; font-family: Poppins, sans-serif; font-size: 1.2rem; color: rgba(255, 255, 255, 0.8); margin-top: 10px; animation: fadeInUp 1s ease;'>Your Gateway to Cryptocurrency Market Intelligence</div>", unsafe_allow_html=True)

# MAIN APP LOGIC
@st.cache_resource
def get_cg(): return CoinGeckoAPI()
try:
    cg = get_cg()
except Exception as e:
    st.error(f"Failed to connect to CoinGecko: {e}")
    st.stop()

# Market Data
@st.cache_data(ttl=30)
def load_market_data(currency):
    return pd.DataFrame(cg.get_coins_markets(vs_currency=currency, per_page=250, price_change_percentage='1h,24h,7d'))

# UI Components
# Create a sidebar with currency options and watchlist
with st.sidebar:
    # Comprehensive currency options with symbols
    currency_options = {
        'USD ($)': 'usd',
        'EUR (€)': 'eur', 
        'GBP (£)': 'gbp',
        'INR (₹)': 'inr',
        'JPY (¥)': 'jpy',
        'CNY (¥)': 'cny',
        'KRW (₩)': 'krw',
        'RUB (₽)': 'rub',
        'CAD ($)': 'cad',
        'AUD ($)': 'aud',
        'CHF (Fr)': 'chf',
        'SEK (kr)': 'sek',
        'NOK (kr)': 'nok',
        'DKK (kr)': 'dkk',
        'PLN (zł)': 'pln',
        'CZK (Kč)': 'czk',
        'HUF (Ft)': 'huf',
        'BGN (лв)': 'bgn',
        'RON (lei)': 'ron',
        'HRK (kn)': 'hrk',
        'TRY (₺)': 'try',
        'ILS (₪)': 'ils',
        'AED (د.إ)': 'aed',
        'SAR (﷼)': 'sar',
        'THB (฿)': 'thb',
        'SGD ($)': 'sgd',
        'MYR (RM)': 'myr',
        'IDR (Rp)': 'idr',
        'PHP (₱)': 'php',
        'VND (₫)': 'vnd',
        'BRL (R$)': 'brl',
        'ARS ($)': 'ars',
        'CLP ($)': 'clp',
        'MXN ($)': 'mxn',
        'ZAR (R)': 'zar',
        'NZD ($)': 'nzd',
        'HKD ($)': 'hkd',
        'TWD ($)': 'twd'
    }
    
    selected_currency_display = st.selectbox("💰 Select Currency", list(currency_options.keys()), index=0)
    currency = currency_options[selected_currency_display]
    
    # Display selected currency info
    st.info(f"Selected: {selected_currency_display}")
    
df = load_market_data(currency)

with st.sidebar:
    st.write("### Watchlist")
    watchlist = st.multiselect('Add to Watchlist', df['name'])

st.subheader("🔍 Search Cryptocurrency")
search_query = st.text_input("Search for a cryptocurrency")

if search_query:
    filtered_data = df[df['name'].str.contains(search_query, case=False, na=False)]
else:
    filtered_data = df

st.write("Showing results for:", search_query or "All")
# Make coin names hyperlinked
def hyperlink_coin_names(row):
    return f"[**{row['name']}**](#chart-{row['symbol']})"

filtered_data['name'] = filtered_data.apply(hyperlink_coin_names, axis=1)
st.write(filtered_data[['name', 'symbol', 'current_price', 'market_cap', 'price_change_percentage_24h']], unsafe_allow_html=True)

# Top Gainers and Losers
st.subheader("📈 Top 10 Gainers / 📉 Losers")
timeframe = st.selectbox("Select Timeframe", ['1h', '24h', '7d'])
gainers = df.nlargest(10, f'price_change_percentage_{timeframe}_in_currency')
losers = df.nsmallest(10, f'price_change_percentage_{timeframe}_in_currency')

st.write("### Gainers")
st.dataframe(gainers[['name', 'symbol', f'price_change_percentage_{timeframe}_in_currency']], height=200)

st.write("### Losers")
st.dataframe(losers[['name', 'symbol', f'price_change_percentage_{timeframe}_in_currency']], height=200)

# Details Section
st.subheader("📊 Cryptocurrency Details and Advanced Chart")
selected_crypto = st.selectbox("Select Cryptocurrency", df['id'].tolist())
crypto_data = df[df['id'] == selected_crypto]
if crypto_data.empty:
    st.warning("No data available for the selected cryptocurrency.")
    st.stop()
crypto_data = crypto_data.squeeze()

# Add hyperlink-based navigation to charts
st.write(f"<div id='chart-{crypto_data['symbol']}'></div>", unsafe_allow_html=True)
st.write(f"**Name**: {crypto_data['name']}")
st.write(f"**Symbol**: {crypto_data['symbol'].upper()}")
# Get currency symbol for display
currency_symbol = selected_currency_display.split('(')[1].split(')')[0]
st.write(f"**Current Price**: {currency_symbol}{crypto_data['current_price']:,.2f}")
if crypto_data['market_cap']:
    st.write(f"**Market Cap**: {currency_symbol}{crypto_data['market_cap']:,.0f}")
else:
    st.write(f"**Market Cap**: N/A")

st.write("### Advanced Chart")

# Enhanced time frame options
col1, col2 = st.columns(2)
with col1:
    time_frame_options = {
        '1 Hour': 1/24,
        '4 Hours': 4/24, 
        '1 Day': 1,
        '1 Week': 7,
        '1 Month': 30,
        '3 Months': 90,
        '6 Months': 180,
        '1 Year': 365
    }
    selected_timeframe = st.selectbox("📊 Time Frame", list(time_frame_options.keys()), index=2)
    
with col2:
    chart_type = st.selectbox("📈 Chart Type", ['Candlestick', 'Line', 'Area'], index=0)

# Technical indicators selection
st.write("#### Technical Indicators")
indicator_cols = st.columns(4)
with indicator_cols[0]:
    show_sma = st.checkbox("SMA (20, 50)", value=True)
with indicator_cols[1]:
    show_rsi = st.checkbox("RSI", value=True)
with indicator_cols[2]:
    show_macd = st.checkbox("MACD", value=True)
with indicator_cols[3]:
    show_bollinger = st.checkbox("Bollinger Bands", value=False)

# Advanced Chart with Technical Indicators
def get_coin_history(coin_id, days=30):
    try:
        data = cg.get_coin_market_chart_by_id(coin_id, vs_currency=currency, days=days)
        prices = data['prices']
        df_hist = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'], unit='ms')
        df_hist.set_index('timestamp', inplace=True)
        return df_hist
    except Exception as e:
        st.error(f"Error loading chart data: {e}")
        return pd.DataFrame()

def create_advanced_chart(df_hist, coin_name):
    if df_hist.empty:
        st.warning("No historical data available")
        return
    
# Calculate technical indicators
    if show_sma:
        df_hist['SMA_20'] = ta.trend.sma_indicator(df_hist['price'], window=20)
        df_hist['SMA_50'] = ta.trend.sma_indicator(df_hist['price'], window=50)
    if show_rsi:
        df_hist['RSI'] = ta.momentum.rsi(df_hist['price'], window=14)
    if show_macd:
        df_hist['MACD'] = ta.trend.macd(df_hist['price'])
    if show_bollinger:
        df_hist['Bollinger_High'] = ta.volatility.bollinger_hband(df_hist['price'])
        df_hist['Bollinger_Low'] = ta.volatility.bollinger_lband(df_hist['price'])
    # Create subplots
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(f'{coin_name} Price Chart', 'RSI', 'MACD'),
        vertical_spacing=0.1,
        row_heights=[0.6, 0.2, 0.2]
    )
    
    # Price chart
    fig.add_trace(
        go.Scatter(x=df_hist.index, y=df_hist['price'], name='Price', line=dict(color='#00D4AA')),
        row=1, col=1
    )
    
    # Add moving averages if selected
    if show_sma:
        fig.add_trace(
            go.Scatter(x=df_hist.index, y=df_hist['SMA_20'], name='SMA 20', line=dict(color='#FF6B6B', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df_hist.index, y=df_hist['SMA_50'], name='SMA 50', line=dict(color='#4ECDC4', width=1)),
            row=1, col=1
        )
    
    # Add Bollinger Bands if selected
    if show_bollinger:
        fig.add_trace(
            go.Scatter(x=df_hist.index, y=df_hist['Bollinger_High'], name='Bollinger High', line=dict(color='#FF9F43', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df_hist.index, y=df_hist['Bollinger_Low'], name='Bollinger Low', line=dict(color='#FF9F43', width=1)),
            row=1, col=1
        )
    
    # RSI if selected
    if show_rsi:
        fig.add_trace(
            go.Scatter(x=df_hist.index, y=df_hist['RSI'], name='RSI', line=dict(color='#FFE66D')),
            row=2, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # MACD if selected
    if show_macd:
        fig.add_trace(
            go.Scatter(x=df_hist.index, y=df_hist['MACD'], name='MACD', line=dict(color='#FF9F43')),
            row=3, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=800,
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        title=f"Technical Analysis for {coin_name}"
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Home button for returning to main page
if st.button('Home'):
    st.experimental_rerun()

# Use the selected time frame
chart_days = int(time_frame_options[selected_timeframe])

with st.spinner("Loading chart data..."):
    hist_data = get_coin_history(selected_crypto, chart_days)
    if not hist_data.empty:
        create_advanced_chart(hist_data, crypto_data['name'])

# Additional crypto details
st.write("### Additional Information")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("24h Change", f"{crypto_data['price_change_percentage_24h']:.2f}%")
with col2:
    st.metric("Market Cap Rank", crypto_data.get('market_cap_rank', 'N/A'))
with col3:
    volume = crypto_data.get('total_volume', 0)
    if volume:
        st.metric("24h Volume", f"{currency_symbol}{volume:,.0f}")
    else:
        st.metric("24h Volume", "N/A")

