import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import sys
import os
from backend.config import TRANSACTIONS_FILE
from backend.services.helper_functions import get_current_price_by_name
from backend.services.stock_agent import query_stock_info
from backend.services.update_data_pipeline import update_finance_data

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


""")
                                            
@st.cache_data(ttl=60)
def load_portfolio():
    if not os.path.exists(TRANSACTIONS_FILE):
        return pd.DataFrame()
    port_df = pd.read_csv(TRANSACTIONS_FILE)
    
    # Use the name-based price lookup for fresh data
    port_df['current_price'] = port_df['name'].apply(get_current_price_by_name)
    return port_df



def run_pipeline_background():
    update_finance_data()
    


st.title("🏠 Portfolio Advisor Dashboard")

portfolio_df = load_portfolio()

if portfolio_df.empty:
    st.info("Your portfolio is empty. Add stocks in the Portfolio page.")
else:
    total_investment = 0.0
    total_current = 0.0
    results = []

    for _, row in portfolio_df.iterrows():
        name = row["name"]
        qty = row["quantity"]
        buy_price = row["price"]
        
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
        
        st.markdown("""
        Welcome! I'm your AI-powered financial assistant. I can analyze market trends, compare companies, and provide data-driven investment outlooks.
        
        **You can ask me things like:**
        * 📈 "Is **Reliance** a good buy right now?"
        * ⚖️ "Compare **Adani Energy** and **NTPC**."
        * 📊 "What is the 30-day return for **Vedanta**?"
        """)

        st.subheader("Quick Actions")
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        user_q = st.chat_input("Ask about stocks like 'Should I buy TCS?'")
        
        active_query = user_q

        if active_query:
            with st.chat_message("user"):
                st.markdown(active_query)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing market data..."):
                    ans = query_stock_info(active_query)
                    st.markdown(ans)

                    