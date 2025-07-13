
# Crypto Trackee

Crypto Trackee is a user-friendly cryptocurrency tracking application that provides real-time market data, historical price charts, and advanced technical analysis features. This application is built using Streamlit and data from the CoinGecko API.

## Features

### 🌍 Multi-Currency Support
- **40+ Currencies**: Choose from a comprehensive list including:
  - USD ($), EUR (€), GBP (£), INR (₹), JPY (¥), CNY (¥), KRW (₩), RUB (₽)
  - CAD ($), AUD ($), CHF (Fr), SEK (kr), NOK (kr), DKK (kr)
  - And many more with their respective symbols

### 📊 Advanced Charting
- **Multiple Time Frames**: 1 Hour, 4 Hours, 1 Day, 1 Week, 1 Month, 3 Months, 6 Months, 1 Year
- **Chart Types**: Candlestick, Line, Area charts
- **Technical Indicators**:
  - Simple Moving Averages (SMA 20, 50)
  - Relative Strength Index (RSI)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands (optional)

### 📈 Market Analysis
- **Real-Time Data**: Live cryptocurrency prices, market caps, and 24h changes
- **Top Gainers/Losers**: Track the best and worst performing cryptocurrencies
- **Search Functionality**: Find specific cryptocurrencies quickly
- **Watchlist**: Create and manage your personalized cryptocurrency watchlist

### 🎨 User Experience
- **Interactive UI**: Beautiful, responsive design with animated elements
- **Sidebar Navigation**: Easy access to currency selection and watchlist
- **Hyperlinked Coins**: Click on coin names to jump to detailed charts
- **Home Button**: Quick navigation back to the main dashboard

## How to Run

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   ```

2. **Navigate to the Directory**:
   ```bash
   cd cryptotrackee-main
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   streamlit run tracker_app_final.py
   ```

5. **Open in Browser**:
   Access the application in your browser via `http://localhost:8502`

6. **Deployed Application**:
   [Crypto Trackee Live](https://cryptotrackee-i67fxyywets55fp74nxwfc.streamlit.app/)

## Technology Stack

- **Frontend**: Streamlit
- **Data Source**: CoinGecko API
- **Charts**: Plotly
- **Technical Analysis**: TA-Lib
- **Data Processing**: Pandas, NumPy
- **Animations**: Lottie

## Dependencies

```
streamlit
pandas
pycoingecko
plotly
requests
streamlit-lottie
streamlit-components
numpy
ta
streamlit-option-menu
```

## Requirements

- Python 3.7+
- All dependencies are listed in `requirements.txt`

## Contributing

Feel free to contribute to this project by opening issues or submitting pull requests.

## License

This project is licensed under the MIT License.
