import streamlit as st
import pandas as pd
import os
from helper_functions import get_current_price_by_name
import threading
import json
from stock_agent import query_stock_info
from update_data import run_data_pipeline
from helper_functions import get_current_price_by_name
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Dashboard - AI Portfolio Advisor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st_autorefresh(interval=60000, key="refresh")

st.sidebar.title("📈 AI FinTech Portfolio Advisor")
st.sidebar.markdown("""
Welcome to your **AI-Powered Stock Portfolio Advisor**.

Use the sidebar navigation:
- Dashboard
- My Portfolio
- Stock Analysis
- Recommendations
- AI Advisor
""")
                                            
@st.cache_data(ttl=60)
def load_portfolio():
    if not os.path.exists("data/user_portfolio.csv"):
        return pd.DataFrame()
    port_df = pd.read_csv("data/user_portfolio.csv")
    
    # Use the name-based price lookup for fresh data
    port_df['current_price'] = port_df['stock_name'].apply(get_current_price_by_name)
    return port_df


LOCK_FILE = "data/pipeline_running.lock"

def run_pipeline_background():
    try:
        run_data_pipeline()
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if not os.path.exists(LOCK_FILE):
    open(LOCK_FILE, "w").close()
    thread = threading.Thread(target=run_pipeline_background, daemon=True)
    thread.start()


st.title("🏠 Portfolio Advisor Dashboard")

portfolio_df = load_portfolio()

if portfolio_df.empty:
    st.info("Your portfolio is empty. Add stocks in the Portfolio page.")
else:
    total_investment = 0.0
    total_current = 0.0
    results = []

    for _, row in portfolio_df.iterrows():
        name = row["stock_name"]
        qty = row["quantity"]
        buy_price = row["buy_price"]
        
        # Robustly fetch current price using the new direct lookup helper
        current_price = get_current_price_by_name(name)
        if current_price is None:
            current_price = buy_price

        investment = buy_price * qty
        current_value = current_price * qty
        profit = current_value - investment
        return_pct = (profit / investment * 100) if investment > 0 else 0

        total_investment += investment
        total_current += current_value

        results.append({
            "Stock": name,
            "Quantity": qty,
            "Buy Price": f"₹{buy_price:,.2f}",
            "Current Price": f"₹{current_price:,.2f}",
            "Profit / Loss": profit,
            "Return %": return_pct
        })

    total_profit = total_current - total_investment
    total_pct_return = (total_profit / total_investment * 100) if total_investment > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Investment", f"₹ {total_investment:,.2f}")
    col2.metric("Current Value", f"₹ {total_current:,.2f}")
    col3.metric("Profit / Loss", f"{total_pct_return:.2f} %",
                delta_color="normal" if total_profit >= 0 else "inverse")

    st.divider()
    col1,col2 = st.columns(2)
    with col1:
        st.subheader("Holdings Overview")
        res_df = pd.DataFrame(results)

        display_df = res_df.style.map(
            lambda val: 'color: green' if val > 0 else ('color: red' if val < 0 else 'color: gray'),
            subset=['Profit / Loss', 'Return %']
        ).format({
            'Profit / Loss': '₹{:,.2f}',
            'Return %': '{:.2f}%'
        })

        st.dataframe(display_df, width="content", hide_index=True)

    with col2:
        
        st.header("🤖 AI Portfolio Advisor")

        user_q = st.chat_input("Ask about stocks like 'Should I buy TCS?'")

        if user_q:
            with st.chat_message("user"):
                st.markdown(user_q)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing market data..."):
                    ans = query_stock_info(user_q)
                    st.markdown(ans)

                    