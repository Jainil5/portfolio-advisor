import streamlit as st
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.update_data import add_stock
from backend.helper_functions import get_current_price_by_name
from backend.stock_agent import query_stock_info

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

# --- FIXED AGENT QUESTION BAR ---
st.markdown("<br/><br/><br/>", unsafe_allow_html=True) # Spacer
with st.container():
    st.markdown("---")
    st.write("### 🤖 Portfolio Advisor Agent")
    q_col, s_col = st.columns([5, 1])
    with q_col:
        user_query = st.text_input("Ask me anything about your portfolio or these stocks...", 
                                  placeholder="e.g., How is my portfolio performing compared to last month?", 
                                  key="portfolio_agent_input",
                                  label_visibility="collapsed")
    with s_col:
        send_pressed = st.button("Send", width='stretch', key="portfolio_agent_send")
    
    if send_pressed and user_query:
        with st.chat_message("user"):
            st.markdown(user_query)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your portfolio..."):
                ans = query_stock_info(user_query)
                st.markdown(ans)
