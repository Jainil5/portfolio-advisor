import streamlit as st
import pandas as pd
import os
from helper_functions import get_current_price_by_name
from stock_agent import query_stock_info

st.set_page_config(page_title="Stock Analysis Pro", page_icon="📈", layout="wide")

# --- HELPER FUNCTIONS ---
def describe_term(title, content):
    """Displays a clean explanation expander for financial terms."""
    with st.expander(f"📚 What is {title}?", expanded=False):
        st.write(content)

# --- DATA LOADING ---
@st.cache_data
def load_data():
    features = pd.read_csv("data/features.csv") if os.path.exists("data/features.csv") else pd.DataFrame()
    return features

features_df = load_data()

# --- SIDEBAR: SELECTION & KEY METRICS ---
with st.sidebar:
    st.title("🔍 Stock Selection")
    stock_map = dict(zip(features_df["stock_id"], features_df["company_name"]))
    selected_id = st.selectbox("Choose Company", options=sorted(stock_map.keys(), key=lambda x: stock_map[x]), format_func=lambda x: stock_map[x])
    
    st.divider()
    
    if selected_id:
        stock_feat = features_df[features_df["stock_id"] == selected_id].iloc[0]
        score = stock_feat.get("score", 0)
        
        # Determine Suggestion
        if score >= 3: 
            suggestion = "BUY"
            color = "#28a745" # Success Green
        elif score >= 1.5: 
            suggestion = "HOLD"
            color = "#ffc107" # Warning Amber
        else: 
            suggestion = "SELL"
            color = "#dc3545" # Danger Red
            
        st.subheader("Key Insight")
        st.metric("AI Score", f"{score:.2f} / 5.0")
        st.markdown(f"### Suggestion: <span style='color:{color}'>{suggestion}</span>", unsafe_allow_html=True)
        
        # Load latest OHLC from price file
        price_file = next((os.path.join("data/prices", f) for f in os.listdir("data/prices") if f.startswith(f"{selected_id}_")), None)
        latest_data = {"High": "N/A", "Low": "N/A", "Close": "N/A", "Price": 0.0}
        
        if price_file:
            pdf_all = pd.read_csv(price_file).dropna(subset=['Close'])
            if not pdf_all.empty:
                last_row = pdf_all.iloc[-1]
                latest_data["High"] = f"₹{last_row['High']:,.2f}"
                latest_data["Low"] = f"₹{last_row['Low']:,.2f}"
                latest_data["Close"] = f"₹{last_row['Close']:,.2f}"
                latest_data["Price"] = last_row['Close']
        
        # Use fallback if price file lookup fails
        current_p = get_current_price_by_name(stock_feat['company_name']) or latest_data["Price"] or stock_feat.get('current_price', 0)
        
        st.divider()
        st.metric("Current Price", f"₹{current_p:,.2f}", f"{stock_feat.get('daily_return', 0):.2f}%")
        
        col_s1, col_s2 = st.columns(2)
        col_s1.markdown(f"**Latest High**\n{latest_data['High']}")
        col_s1.markdown(f"**Latest Low**\n{latest_data['Low']}")
        col_s2.markdown(f"**Latest Close**\n{latest_data['Close']}")
        col_s2.markdown(f"**Sector**\n{stock_feat.get('sector', 'N/A')}")

    st.divider()
    with st.expander("ℹ️ Help & Info"):
        st.write("**Scoring**: Based on technical momentum and fundamental health.")
        st.write("**Agent**: AI-powered assistant using RAG technology.")

# --- MAIN CONTENT: SCROLLABLE DASHBOARD ---
st.title("📈 Stock Intelligence Dashboard")

if selected_id:
    # Main scrollable container
    main_container = st.container(height=650, border=True)
    
    with main_container:
        tab_analysis, tab_company = st.tabs(["📊 Performance Analysis", "🏢 Company Details"])
        
        with tab_analysis:
            # 1. Performance and Risk Metrics
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.subheader("Performance Returns")
                describe_term("Returns", "Returns are calculated as the percentage change in the stock price over a specific timeframe (1 Week, 1 Month, or 1 Year). Positive returns represent profit, while negative returns represent a loss.")
                st.metric("1 Week Return", f"{stock_feat.get('return_7d', 0):.2f}%")
                st.metric("1 Month Return", f"{stock_feat.get('return_30d', 0):.2f}%")
                st.metric("1 Year Return", f"{stock_feat.get('return_180d', 0):.2f}%")
            
            with m_col2:
                st.subheader("Risk & Volatility")
                describe_term("Volatility", "Volatility measures the degree of variation in a trading price series over time. High volatility indicates that the stock price can change dramatically in a short period in either direction, representing higher risk.")
                st.metric("1 Week Volatility", f"{stock_feat.get('volatility_7d', 0):.2f}%")
                st.metric("1 Month Volatility", f"{stock_feat.get('volatility_30d', 0):.2f}%")
                st.metric("1 Year Volatility", f"{stock_feat.get('volatility_180d', 0):.2f}%")
            
            st.divider()
            
            # 2. Side-by-Side Charts (7D and 30D)
            st.subheader("Price Action View")
            price_file = next((os.path.join("data/prices", f) for f in os.listdir("data/prices") if f.startswith(f"{selected_id}_")), None)
            if price_file:
                pdf = pd.read_csv(price_file)
                pdf['Date'] = pd.to_datetime(pdf['Date'], utc=True)
                pdf = pdf.sort_values('Date').dropna(subset=['Close'])
                
                c_sub1, c_sub2 = st.columns(2)
                with c_sub1:
                    st.write("**Recent Weekly Trend (7 Days)**")
                    recent_7 = pdf.tail(7)
                    st.line_chart(recent_7.set_index('Date')['Close'], color="#29b5e8", height=250)
                
                with c_sub2:
                    st.write("**Monthly Performance (30 Days)**")
                    recent_30 = pdf.tail(30)
                    st.area_chart(recent_30.set_index('Date')['Close'], color="#FF4B4B", height=250)
            else:
                st.info("Historical charts currently unavailable.")

        with tab_company:
            st.subheader("Fundamental Metrics")
            describe_term("Key Fundamentals", """
            - **Market Cap**: Total market value of a company's outstanding shares.
            - **Debt to Equity**: Compares total liabilities to shareholder equity. High values suggest more debt-reliant growth.
            - **Cash Ratio**: Measures ability to pay short-term debt using only cash.
            """)
            f1, f2, f3 = st.columns(3)
            f1.metric("Market Cap", stock_feat.get('market_cap', 'N/A'))
            f2.metric("Debt/Equity", f"{stock_feat.get('debt_to_equity', 0):.2f}")
            f3.metric("Cash Ratio", f"{stock_feat.get('cash_ratio', 0):.2f}")
            
            st.divider()
            st.subheader("Company Profile")
            st.markdown(f"**Industry:** {stock_feat.get('industry', 'N/A')}")
            st.markdown(f"**Sector:** {stock_feat.get('sector', 'N/A')}")
            st.markdown(f"**Exchange:** {stock_feat.get('exchange', 'N/A')}")
            st.markdown(f"**Ticker Symbol:** {stock_feat.get('ticker', 'N/A')}")

# --- PERSISTENT AGENT QUESTION BAR (BOTTOM) ---
st.markdown("---")
st.write("### 🤖 Portfolio Advisor Agent")
q_col, s_col = st.columns([5, 1])
with q_col:
    user_query = st.text_input("Ask me anything about this stock or your portfolio...", 
                              placeholder="e.g., How does the 30-day return look?", 
                              key="analysis_page_agent_input",
                              label_visibility="collapsed")
with s_col:
    send_pressed = st.button("Send", key="analysis_page_agent_send", width='stretch')

if send_pressed and user_query:
    with st.chat_message("user"):
        st.markdown(user_query)
    with st.chat_message("assistant"):
        with st.spinner("Analyzing market data..."):
            ans = query_stock_info(user_query)
            st.markdown(ans)