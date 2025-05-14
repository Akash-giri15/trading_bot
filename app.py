import streamlit as st
from trading_bot import BasicBot  # Ensure BasicBot class is defined in backend.py

st.set_page_config(page_title="Binance Bot UI", layout="wide")
st.title("Binance Trading Bot UI")

# Sidebar for API credentials and settings
st.sidebar.header("API & Settings")
api_key = st.sidebar.text_input("API Key", type="password")
api_secret = st.sidebar.text_input("API Secret", type="password")
testnet = st.sidebar.checkbox("Use Testnet", value=True)

# Main inputs
st.header("Place an Order or Execute Strategy")
symbol = st.text_input("Symbol (e.g., BTCUSDT)")
side = st.selectbox("Side", ["BUY", "SELL"])
order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP_LIMIT", "TWAP", "GRID"])
quantity = st.number_input("Quantity", min_value=0.0, format="%.8f")

# Conditional inputs based on order type
price = None
stop_price = None
duration = None
intervals = None
lower_price = None
upper_price = None
grids = None

if order_type in ["LIMIT", "STOP_LIMIT"]:
    price = st.number_input("Price", min_value=0.0, format="%.8f")
if order_type == "STOP_LIMIT":
    stop_price = st.number_input("Stop Price", min_value=0.0, format="%.8f")
if order_type == "TWAP":
    duration = st.number_input("Total Duration (seconds)", min_value=1)
    intervals = st.number_input("Number of Intervals", min_value=1)
if order_type == "GRID":
    lower_price = st.number_input("Lower Price", min_value=0.0, format="%.8f")
    upper_price = st.number_input("Upper Price", min_value=0.0, format="%.8f")
    grids = st.number_input("Number of Grid Levels", min_value=1)

# Place order button
if st.button("Execute"):
    if not api_key or not api_secret:
        st.error("API Key and Secret are required.")
    elif not symbol:
        st.error("Symbol is required.")
    else:
        try:
            bot = BasicBot(api_key, api_secret, testnet=testnet)
            if order_type in ["MARKET", "LIMIT", "STOP_LIMIT"]:
                result = bot.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price
                )
            elif order_type == "TWAP":
                if duration is None or intervals is None:
                    st.error("TWAP requires duration and intervals.")
                    st.stop()
                result = bot.execute_twap(
                    symbol=symbol,
                    side=side,
                    total_qty=quantity,
                    duration=int(duration),
                    intervals=int(intervals)
                )
            elif order_type == "GRID":
                if lower_price is None or upper_price is None or grids is None:
                    st.error("GRID requires lower price, upper price, and grids.")
                    st.stop()
                result = bot.execute_grid(
                    symbol=symbol,
                    side=side,
                    total_qty=quantity,
                    lower_price=lower_price,
                    upper_price=upper_price,
                    grids=int(grids)
                )
            st.success("Order executed successfully!")
            st.json(result)
        except Exception as e:
            st.error(f"Error executing order: {e}")
