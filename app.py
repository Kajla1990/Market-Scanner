import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Market Scanner Terminal",
    layout="wide"
)

# --- 2. SESSION STATE ---
if "balance" not in st.session_state:
    st.session_state.balance = 500000.0
if "trades" not in st.session_state:
    st.session_state.trades = []

# --- 3. CALCULATE INDICATORS ---
def calculate_indicators(df):
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_15'] = df['Close'].ewm(span=15, adjust=False).mean()
    df['MA_5D'] = df['Close'].rolling(window=5).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['Support_5D'] = df['Low'].rolling(window=5).min()
    df['Resistance_5D'] = df['High'].rolling(window=5).max()
    return df

# --- 4. SIDEBAR CONTROLS ---
st.sidebar.header("🌐 Market Settings")
ticker_symbol = st.sidebar.text_input("Enter Ticker Symbol", "RELIANCE.NS")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1d", "1h", "15m"])

# --- 5. MAIN APP ---
st.title("🚀 Advanced Market Scanner & Trading Terminal")

@st.cache_data(ttl=300)
def load_data(ticker, tf):
    try:
        data = yf.download(ticker, period="60d", interval=tf, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except:
        return None

df = load_data(ticker_symbol, timeframe)

if df is None or df.empty:
    st.error("Could not fetch data. Please check the ticker symbol (e.g., RELIANCE.NS, TCS.NS, BTC-USD).")
else:
    df = calculate_indicators(df)
    
    latest_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2])
    pct_diff = ((latest_price - prev_price) / prev_price) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Live Price", f"₹{latest_price:.2f}", f"{pct_diff:.2f}%")
    col2.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")
    col3.metric("Support (5D)", f"₹{df['Support_5D'].iloc[-1]:.2f}")
    col4.metric("Resistance (5D)", f"₹{df['Resistance_5D'].iloc[-1]:.2f}")

    st.subheader(f"📊 Price Chart for {ticker_symbol}")
    st.line_chart(df[['Close', 'EMA_9', 'EMA_15']])

    st.subheader("💼 Paper Trading Demo")
    qty = st.number_input("Quantity", min_value=1, value=10)
    if st.button("Buy / Long"):
        cost = latest_price * qty
        if st.session_state.balance >= cost:
            st.session_state.balance -= cost
            st.session_state.trades.append({"Type": "BUY", "Ticker": ticker_symbol, "Price": latest_price, "Qty": qty})
            st.success(f"Successfully bought {qty} shares of {ticker_symbol}!")
        else:
            st.error("Insufficient demo balance!")
            
    st.write(f"**Demo Account Balance:** ₹{st.session_state.balance:,.2f}")
    if st.session_state.trades:
        st.write("**Trade History:**")
        st.table(pd.DataFrame(st.session_state.trades))
