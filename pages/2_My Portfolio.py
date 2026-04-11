import streamlit as st
import pandas as pd
import os
from user_data import add_stock
from helper_functions import get_current_price_by_name

st.set_page_config(page_title="Portfolio", page_icon="💼", layout="wide")
st.title("💼 Your Portfolio")

PORTFOLIO_FILE = "data/user_portfolio.csv"
STOCKS_FILE = "data/stocks.csv"

# === 1. Add Stock Section ===
with st.expander("➕ Add New Stock to Portfolio", expanded=False):
    st.markdown("Select a stock from the backend database to add it to your tracking.")
    if os.path.exists(STOCKS_FILE):
        stocks_db = pd.read_csv(STOCKS_FILE)
        active_stocks = stocks_db[stocks_db['is_active'] == True]
        stock_options = active_stocks.set_index('stock_id')['company_name'].to_dict()
        
        with st.form("add_stock_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_val = st.selectbox("Company", options=list(stock_options.keys()), format_func=lambda x: stock_options[x])
            with col2:
                qty = st.number_input("Quantity", min_value=1, step=1)
            with col3:
                price = st.number_input("Buy Price (₹)", min_value=0.0, step=0.1)
                
            submitted = st.form_submit_button("Add Stock")
            if submitted:
                add_stock(selected_val, qty, price)
                st.success(f"Added {qty} shares of {stock_options[selected_val]}!")
                st.rerun()
    else:
        st.warning("Stocks Database missing. Fetch stocks first.")

st.divider()

# === 2. Portfolio Table ===
if not os.path.exists(PORTFOLIO_FILE):
    st.info("Portfolio is empty.")
    st.stop()

portfolio_df = pd.read_csv(PORTFOLIO_FILE)
if portfolio_df.empty:
    st.info("Portfolio is empty.")
    st.stop()
    
# No longer merging with features.csv here, we use the direct lookup in the loop

results = []
for _, row in portfolio_df.iterrows():
    s_id = row["stock_id"]
    name = row["stock_name"]
    qty = row["quantity"]
    buy_price = row["buy_price"]

    # Use the fresh lookup helper
    current_price = get_current_price_by_name(name)
    if current_price is None:
        current_price = buy_price

    investment = buy_price * qty
    current_value = current_price * qty
    profit = current_value - investment
    return_pct = (profit / investment) * 100 if investment > 0 else 0

    results.append({
        "Stock": name,
        "Quantity": qty,
        "Buy Price": f"₹{buy_price:,.2f}",
        "Current Price": f"₹{current_price:,.2f}",
        "Profit / Loss": profit,
        "Return %": return_pct
    })

res_df = pd.DataFrame(results)

# Highlighting best/worst
best_stock = res_df.loc[res_df['Return %'].idxmax()]
worst_stock = res_df.loc[res_df['Return %'].idxmin()]

c1, c2 = st.columns(2)
with c1:
    st.success(f"**Best Performer:** {best_stock['Stock']} ({best_stock['Return %']:.2f}%)")
with c2:
    st.error(f"**Worst Performer:** {worst_stock['Stock']} ({worst_stock['Return %']:.2f}%)")

st.subheader("Holdings Overview")
# Format display dataframe safely
display_df = res_df.style.map(
    lambda val: 'color: green' if val > 0 else ('color: red' if val < 0 else 'color: gray'),
    subset=['Profit / Loss', 'Return %']
).format({
    'Profit / Loss': '₹{:,.2f}',
    'Return %': '{:.2f}%'
})

st.dataframe(display_df, width="content")

st.subheader("Investment Distribution")
st.bar_chart(res_df, x="Stock", y="Return %", color="#4CAF50")
