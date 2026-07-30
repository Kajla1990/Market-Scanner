import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Pro Trading & Candlestick Terminal",
    layout="wide"
)

# --- 2. SESSION STATE ---
if "balance" not in st.session_state:
    st.session_state.balance = 500000.0
if "trades" not in st.session_state:
    st.session_state.trades = []

# --- 3. SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Pro Terminal Settings")
ticker_symbol = st.sidebar.text_input("Enter Ticker Symbol", "RELIANCE.NS")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1d", "1h", "15m"])

# --- 4. MAIN APP ---
st.title("📈 Pro Candlestick Trading & Scanner Terminal")

@st.cache_data(ttl=300)
def load_data(ticker, tf):
    try:
        data = yf.download(ticker, period="60d", interval=tf, progress=False)
        if data is None or data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        return data
    except:
        return None

df = load_data(ticker_symbol, timeframe)

if df is None or df.empty or len(df) < 5:
    st.error("Could not fetch valid data. Please check the ticker symbol (e.g., RELIANCE.NS, TCS.NS, BTC-USD).")
else:
    # Indicators calculation
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['Support'] = df['Low'].rolling(window=10).min()
    df['Resistance'] = df['High'].rolling(window=10).max()
    df = df.dropna()

    if not df.empty:
        latest_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        pct_diff = ((latest_price - prev_price) / prev_price) * 100
        
        rsi_val = float(df['RSI'].iloc[-1])
        supp_val = float(df['Support'].iloc[-1])
        ress_val = float(df['Resistance'].iloc[-1])

        # Metrics display
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Live Price", f"₹{latest_price:.2f}", f"{pct_diff:.2f}%")
        col2.metric("RSI (14)", f"{rsi_val:.2f}")
        col3.metric("Support", f"₹{supp_val:.2f}")
        col4.metric("Resistance", f"₹{ress_val:.2f}")

        # --- PROFESSIONAL CANDLESTICK CHART (PLOTLY) ---
        st.subheader(f"🕯️ Advanced Candlestick Chart for {ticker_symbol}")
        
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Candlestick'
        )])
        
        # Add EMAs to chart
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], mode='lines', name='EMA 9', line=dict(color='orange', width=1.5)))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], mode='lines', name='EMA 21', line=dict(color='cyan', width=1.5)))

        fig.update_layout(
            template='plotly_dark',
            xaxis_rangeslider_visible=False,
            height=500,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # --- PAPER TRADING SECTION ---
        st.subheader("💼 Paper Trading Terminal")
        qty = st.number_input("Quantity", min_value=1, value=10)
        
        col_buy, col_sell = st.columns(2)
        with col_buy:
            if st.button("🟢 Buy / Long"):
                cost = latest_price * qty
                if st.session_state.balance >= cost:
                    st.session_state.balance -= cost
                    st.session_state.trades.append({"Type": "BUY", "Ticker": ticker_symbol, "Price": latest_price, "Qty": qty})
                    st.success(f"Successfully bought {qty} shares of {ticker_symbol}!")
                else:
                    st.error("Insufficient demo balance!")
                    
        with col_sell:
            if st.button("🔴 Sell / Short"):
                st.session_state.balance += (latest_price * qty)
                st.session_state.trades.append({"Type": "SELL", "Ticker": ticker_symbol, "Price": latest_price, "Qty": qty})
                st.success(f"Successfully sold {qty} shares of {ticker_symbol}!")

        st.write(f"**Demo Account Balance:** ₹{st.session_state.balance:,.2f}")
        
        if st.session_state.trades:
            st.write("**Trade History:**")
            st.table(pd.DataFrame(st.session_state.trades))
    else:
        st.warning("Insufficient data points after cleaning. Try a different timeframe.")
