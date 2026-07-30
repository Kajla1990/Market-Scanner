import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. PAGE CONFIGURATION & MOBILE/PC FRIENDLINESS ---
st.set_page_config(
    page_title="Advanced Ultra Trading & Backtesting Terminal",
    page_layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE & PAPER TRADING INITIALIZATION ---
if "balance" not in st.session_state:
    st.session_state.balance = 500000.0  # 5,00,000 INR Demo Money
if "trades" not in st.session_state:
    st.session_state.trades = []
if "trade_count_today" not in st.session_state:
    st.session_state.trade_count_today = 0

# --- 3. HELPER FUNCTIONS: TECHNICAL INDICATORS & ANALYSIS ---
def calculate_indicators(df):
    # EMA 9 and EMA 15
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_15'] = df['Close'].ewm(span=15, adjust=False).mean()
    
    # 5-Day Moving Average of Close
    df['MA_5D'] = df['Close'].rolling(window=5).mean()
    
    # Volume spike calculation (Comparing with 15-period volume average)
    df['Vol_Avg_15'] = df['Volume'].rolling(window=15).mean()
    df['Vol_Change_Pct'] = ((df['Volume'] - df['Vol_Avg_15']) / df['Vol_Avg_15']) * 100
    
    # RSI 14 calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Automated 5-Day Support & Resistance
    df['Support_5D'] = df['Low'].rolling(window=5).min()
    df['Resistance_5D'] = df['High'].rolling(window=5).max()
    
    return df

def detect_signals_and_patterns(df):
    signals = []
    for i in range(2, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Conditions check
        ema_channel = (curr['Close'] >= min(curr['EMA_9'], curr['EMA_15'])) and (curr['Close'] <= max(curr['EMA_9'], curr['EMA_15']))
        vol_spike = curr['Volume'] > (1.5 * curr['Vol_Avg_15'])
        near_support = abs(curr['Close'] - curr['Support_5D']) / curr['Support_5D'] < 0.005
        near_resistance = abs(curr['Close'] - curr['Resistance_5D']) / curr['Resistance_5D'] < 0.005
        
        pattern_text = "Normal Price Action"
        signal_type = "HOLD"
        
        # Candlestick Rejection Logic (Hammer / Shooting Star simulation)
        body = abs(curr['Close'] - curr['Open'])
        range_val = curr['High'] - curr['Low']
        
        if range_val > 0:
            lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
            upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
            
            if lower_wick > (2 * body) and near_support:
                pattern_text = "Bullish Rejection / Hammer at Support"
                if vol_spike:
                    signal_type = "BUY"
            elif upper_wick > (2 * body) and near_resistance:
                pattern_text = "Bearish Rejection / Shooting Star at Resistance"
                if vol_spike:
                    signal_type = "SELL"
                    
        signals.append({
            "Date": df.index[i],
            "Price": curr['Close'],
            "Signal": signal_type,
            "Pattern": pattern_text,
            "Volume_Change": f"{curr['Vol_Change_Pct']:.1f}%",
            "RSI": f"{curr['RSI']:.1f}"
        })
    return pd.DataFrame(signals)

# --- 4. SIDEBAR: GLOBAL CONTROLS & ASSET SELECTION ---
st.sidebar.header("🌐 Global Markets & Assets")
market_type = st.sidebar.selectbox("Select Market Type", ["Indian Stocks (NSE)", "US Stocks / Forex", "Cryptocurrency", "Global Indices"])

if market_type == "Indian Stocks (NSE)":
    default_ticker = "RELIANCE.NS"
elif market_type == "US Stocks / Forex":
    default_ticker = "AAPL"
elif market_type == "Cryptocurrency":
    default_ticker = "BTC-USD"
else:
    default_ticker = "^NSEI"

ticker_symbol = st.sidebar.text_input("Enter Ticker Symbol", default_ticker)
timeframe = st.sidebar.selectbox("Select Timeframe", ["1d", "1h", "15m", "5m"])

st.sidebar.markdown("---")
st.sidebar.header("⚡ Custom Indicator Settings")
show_indicator = st.sidebar.checkbox("Apply Advanced Custom Indicator", value=True)
show_support_resistance = st.sidebar.checkbox("Show Auto 5-Day Support/Resistance", value=True)
price_alert_val = st.sidebar.number_input("Set Price Alert Target (INR/USD)", value=0.0)

# --- 5. MAIN INTERFACE ---
st.title("🚀 Advanced Multi-Asset Ultra Trading Terminal")
st.markdown("Powered by 9/15 EMA, 5D MA, Volume Analyzer, Rejection Patterns, RSI, Paper Trading & Replay Facility.")

# Fetching Data Safely with Error Handling & Anti-Hang Protection
@st.cache_data(ttl=300)
def load_data(ticker, period_tf):
    try:
        data = yf.download(ticker, period="60d", interval=period_tf, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except Exception as e:
        return None

data_load_state = st.text("Loading market data...")
df = load_data(ticker_symbol, timeframe)
data_load_state.text("")

if df is None or df.empty:
    st.error("Error: Could not fetch data. Please check the ticker symbol or network connection (Safety Protection Triggered).")
else:
    df = calculate_indicators(df)
    
    # Price Alert Checker
    if price_alert_val > 0:
        latest_cp = df['Close'].iloc[-1]
        if latest_cp >= price_alert_val:
            st.warning(f"🚨 PRICE ALERT TRIGGERED! Current Price {latest_cp} has reached or crossed target {price_alert_val}")

    # --- 6. METRICS & LIVE MARKET OVERVIEW ---
    latest_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2])
    price_diff = latest_price - prev_price
    pct_diff = (price_diff / prev_price) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Live Price", f"{latest_price:.2f}", f"{pct_diff:.2f}%")
    col2.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")
    col3.metric("Volume Change vs 15MA", f"{df['Vol_Change_Pct'].iloc[-1]:+.1f}%")
    col4.metric("Demo Account Balance", f"₹{st.session_state.balance:,.2f}")

    # --- 7. ADVANCED CHART & INDICATOR VISUALIZATION ---
    st.subheader(f"📊 Chart Analysis & Custom Indicator for {ticker_symbol}")
    
    if show_indicator:
        chart_data = df[['Close', 'EMA_9', 'EMA_15', 'MA_5D']]
        st.line_chart(chart_data)
        st.caption("Indicator Layers Active: 9 EMA (Blue-ish), 15 EMA (Orange), 5D Moving Average (Green), embedded with RSI & Volume Matrix.")
    else:
        st.line_chart(df['Close'])

    if show_support_resistance:
        st.info(f" automático 5-Day Support: ₹{df['Support_5D'].iloc[-1]:.2f} | Resistance: ₹{df['Resistance_5D'].iloc[-1]:.2f}")

    # --- 8. SIGNAL SCANNER & PATTERN TEXT LOGS ---
    st.subheader("🔍 Pattern Rejection & Fast Trade Signals Log")
    signals_df = detect_signals_and_patterns(df)
    
    if not signals_df.empty:
        st.dataframe(signals_df.tail(10), use_container_width=True)
    else:
        st.info("No prominent breakout/rejection patterns found in current data window.")

    # --- 9. BACKTESTING / MARKET REPLAY FACILITY ---
    st.markdown("---")
    st.subheader("⏪ Market Replay & Accuracy Check Facility")
    replay_index = st.slider("Scrub through historical candles to test indicator accuracy:", 15, len(df)-1, len(df)-1)
    replay_row = df.iloc[replay_index]
    st.write(f"**Replay Timestamp:** {df.index[replay_index]} | **Price:** {replay_row['Close']:.2f} | **RSI:** {replay_row['RSI']:.2f} | **Volume Spike:** {replay_row['Vol_Change_Pct']:.1f}%")

    # --- 10. PAPER TRADING SYSTEM (5,00,000 INR Demo & Limits) ---
    st.markdown("---")
    st.subheader("💼 Paper Trading Terminal (Demo Mode)")
    
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        trade_action = st.radio("Action", ["BUY / LONG", "SELL / SHORT"])
    with t_col2:
        trade_qty = st.number_input("Quantity / Lots", min_value=1, value=10)
    with t_col3:
        st.write("")
        st.write("")
        top_up_btn = st.button("Top Up Demo Funds (+₹1,00,000)")
        if top_up_btn:
            st.session_state.balance += 100000.0
            st.success("Demo account topped up successfully!")

    if st.button("Execute Paper Trade"):
        if st.session_state.trade_count_today >= 10:
            st.error("Daily trade limit reached! Maximum 10 trades per day allowed in paper trading.")
        else:
            trade_value = latest_price * trade_qty
            if trade_action == "BUY / LONG" and st.session_state.balance >= trade_value:
                st.session_state.balance -= trade_value
                st.session_state.trades.append({"Type": "BUY", "Ticker": ticker_symbol, "Price": latest_price, "Qty": trade_qty})
                st.session_state.trade_count_today += 1
                st.success(f"Executed BUY order for {trade_qty} shares of {ticker_symbol} at ₹{latest_price:.2f}")
            elif trade_action == "SELL / SHORT":
                st.session_state.balance += trade_value
                st.session_state.trades.append({"Type": "SELL", "Ticker": ticker_symbol, "Price": latest_price, "Qty": trade_qty})
                st.session_state.trade_count_today += 1
                st.success(f"Executed SELL order for {trade_qty} shares of {ticker_symbol} at ₹{latest_price:.2f}")
            else:
                st.error("Insufficient demo funds for this transaction!")

    if st.session_state.trades:
        st.write(f"**Active/Executed Trades History Today (Limit: {st.session_state.trade_count_today}/10):**")
        st.table(pd.DataFrame(st.session_state.trades))
