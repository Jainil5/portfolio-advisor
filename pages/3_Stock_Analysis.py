import os
import sys
import streamlit as st
import pandas as pd
# Add project root to PYTHONPATH for backend imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

# Define data directories using PROJECT_ROOT
DATA_DIR = os.path.join(PROJECT_ROOT, 'backend', 'data')
PRICES_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, 'data', 'prices'))

from backend.services.helper_functions import get_current_price_by_name
from backend.services.stock_agent import query_stock_info

st.set_page_config(page_title="Stock Analysis Pro", page_icon="📈", layout="wide")

# --- HELPER FUNCTIONS ---
def describe_term(title, content):
    """Displays a clean explanation expander for financial terms."""
    with st.expander(f"📚 What is {title}?", expanded=False):
        st.write(content)

# --- DATA LOADING ---
@st.cache_data
def load_data():
    features = pd.read_csv(os.path.join(DATA_DIR, "features.csv")) if os.path.exists(os.path.join(DATA_DIR, "features.csv")) else pd.DataFrame()
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
        price_file = next((os.path.join(PRICES_DIR, f) for f in os.listdir(PRICES_DIR) if f.startswith(f"{selected_id}_")), None)
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

# --- MAIN CONTENT: DASHBOARD ---
st.title("📈 Stock Intelligence Dashboard")

if selected_id:
    # Main container without fixed height for better scrolling and readability
    main_container = st.container(border=True)
    
    with main_container:
        tab_technicals, tab_volatility, tab_fundamentals = st.tabs([
            "📈 Price & Technicals", 
            "📊 Volatility & Volume", 
            "🏢 Fundamentals & Profile"
        ])
        
        # Load historical price file for charting and technical indicators
        price_file = next((os.path.join("data/prices", f) for f in os.listdir("data/prices") if f.startswith(f"{selected_id}_")), None)
        pdf = pd.DataFrame()
        if price_file:
            pdf = pd.read_csv(price_file)
            pdf['Date'] = pd.to_datetime(pdf['Date'], utc=True)
            pdf = pdf.sort_values('Date').dropna(subset=['Close'])
            
            # Pre-compute SMA20 and SMA50 on the entire historical series for accuracy
            pdf['MA20'] = pdf['Close'].rolling(20, min_periods=1).mean()
            pdf['MA50'] = pdf['Close'].rolling(50, min_periods=1).mean()
        
        # --- TAB 1: PRICE & TECHNICAL INDICATORS ---
        with tab_technicals:
            if not pdf.empty:
                # Timeframe Selector & Chart Header
                col_chart_title, col_timeframe = st.columns([2, 1])
                with col_chart_title:
                    st.subheader("Historical Price & Moving Averages")
                with col_timeframe:
                    selected_timeframe = st.radio(
                        "Timeframe Selection",
                        options=["1W", "1M", "3M", "1Y"],
                        index=1, # Default to 1M
                        horizontal=True,
                        key="chart_timeframe_selector",
                        label_visibility="collapsed"
                    )
                
                # Filter data based on selected timeframe
                max_date = pdf['Date'].max()
                if selected_timeframe == "1W":
                    filtered_pdf = pdf[pdf['Date'] >= max_date - pd.Timedelta(days=7)]
                    if len(filtered_pdf) < 2:
                        filtered_pdf = pdf.tail(7)
                elif selected_timeframe == "1M":
                    filtered_pdf = pdf[pdf['Date'] >= max_date - pd.Timedelta(days=30)]
                    if len(filtered_pdf) < 5:
                        filtered_pdf = pdf.tail(30)
                elif selected_timeframe == "3M":
                    filtered_pdf = pdf[pdf['Date'] >= max_date - pd.Timedelta(days=90)]
                    if len(filtered_pdf) < 15:
                        filtered_pdf = pdf.tail(90)
                elif selected_timeframe == "1Y":
                    filtered_pdf = pdf[pdf['Date'] >= max_date - pd.Timedelta(days=365)]
                    if len(filtered_pdf) < 50:
                        filtered_pdf = pdf.tail(252)
                
                # Format dataframe for Streamlit line_chart
                chart_data = filtered_pdf.rename(columns={
                    'Close': 'Price',
                    'MA20': '20-Day SMA',
                    'MA50': '50-Day SMA'
                }).set_index('Date')[['Price', '20-Day SMA', '50-Day SMA']]
                
                # Display the beautiful chart
                st.line_chart(chart_data, height=350)
                
                st.divider()
                
                # Technical Indicators Grid
                st.subheader("Technical Indicator Insights")
                
                # Get latest values for indicators
                latest_row = pdf.iloc[-1]
                latest_close = latest_row['Close']
                latest_ma20 = latest_row['MA20']
                latest_ma50 = latest_row['MA50']
                
                ma_gap = ((latest_ma20 - latest_ma50) / latest_ma50) * 100 if latest_ma50 else 0
                ma_crossover = "Bullish (Golden Cross) 🟢" if latest_ma20 > latest_ma50 else "Bearish (Death Cross) 🔴"
                price_vs_ma20 = ((latest_close - latest_ma20) / latest_ma20) * 100 if latest_ma20 else 0
                
                high_52w = stock_feat.get('52w_high', 0.0) or pdf['High'].tail(252).max()
                low_52w = stock_feat.get('52w_low', 0.0) or pdf['Low'].tail(252).min()
                
                if (high_52w - low_52w) > 0:
                    range_pos = (current_p - low_52w) / (high_52w - low_52w)
                    range_pos = max(0.0, min(1.0, range_pos))
                else:
                    range_pos = 0.5
                
                t_col1, t_col2, t_col3 = st.columns(3)
                
                # Column 1: Trend Strength
                with t_col1:
                    st.markdown("##### Trend Strength")
                    st.metric("Moving Average Crossover", ma_crossover, f"{ma_gap:+.2f}% gap")
                    st.markdown(f"**AI Score:** `{score:.2f} / 5.0`")
                
                # Column 2: Moving Averages Values
                with t_col2:
                    st.markdown("##### Moving Averages")
                    st.metric("20-Day SMA", f"₹{latest_ma20:,.2f}")
                    st.metric("50-Day SMA", f"₹{latest_ma50:,.2f}", f"{price_vs_ma20:+.2f}% vs Price")
                
                # Column 3: 52-Week Range Visual Indicator
                with t_col3:
                    st.markdown("##### 52-Week Price Range")
                    st.markdown(f"Current price is **₹{current_p:,.2f}**")
                    st.progress(range_pos)
                    st.markdown(
                        f"<div style='display: flex; justify-content: space-between; font-size: 0.82rem; color: gray; margin-top: -10px;'>"
                        f"<span>Low: ₹{low_52w:,.2f}</span>"
                        f"<span>High: ₹{high_52w:,.2f}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                
                st.divider()
                describe_term("Technical Indicators", """
                - **20-Day & 50-Day SMA**: Simple Moving Averages showing the average closing price over the last 20 or 50 trading days.
                - **Golden Cross / Death Cross**: Occurs when the short-term MA (20-day) crosses above (Bullish) or below (Bearish) the long-term MA (50-day), signaling momentum changes.
                - **52-Week Range**: Displays where the current price stands relative to its highest and lowest transaction values over the past year.
                """)
            else:
                st.info("Price history is currently unavailable for technical indicator calculations.")
                
        # --- TAB 2: VOLATILITY & VOLUME ---
        with tab_volatility:
            st.subheader("Performance & Volatility Profile")
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.markdown("##### Performance Returns")
                st.metric("1 Week Return", f"{stock_feat.get('return_7d', 0):.2f}%")
                st.metric("1 Month Return", f"{stock_feat.get('return_30d', 0):.2f}%")
                st.metric("1 Year Return", f"{stock_feat.get('return_180d', 0):.2f}%")
            
            with m_col2:
                st.markdown("##### Risk & Volatility")
                st.metric("1 Week Volatility", f"{stock_feat.get('volatility_7d', 0):.2f}%")
                st.metric("1 Month Volatility", f"{stock_feat.get('volatility_30d', 0):.2f}%")
                st.metric("1 Year Volatility", f"{stock_feat.get('volatility_180d', 0):.2f}%")
            
            st.divider()
            
            st.subheader("Volume & Liquidity Analysis")
            vol_col1, vol_col2, vol_col3, vol_col4 = st.columns(4)
            
            latest_vol = latest_data.get("Volume", 0) if not pdf.empty else 0
            avg_vol_30 = stock_feat.get('avg_volume_30d', 0)
            vol_delta = ((latest_vol - avg_vol_30) / avg_vol_30 * 100) if avg_vol_30 else 0
            
            vol_col1.metric("Latest Day Volume", f"{latest_vol:,}" if latest_vol else "N/A", f"{vol_delta:+.1f}% vs 30D Avg" if latest_vol and avg_vol_30 else None)
            vol_col2.metric("7-Day Avg Volume", f"{int(stock_feat.get('avg_volume_7d', 0)):,}")
            vol_col3.metric("30-Day Avg Volume", f"{int(avg_vol_30):,}")
            vol_col4.metric("180-Day Avg Volume", f"{int(stock_feat.get('avg_volume_180d', 0)):,}")
            
            st.divider()
            describe_term("Volatility & Volume", """
            - **Volatility**: Measures the degree of variation in trading prices. High volatility represents higher risk and rapid swings.
            - **Average Volume**: The average number of shares traded per day. Higher volume indicates higher liquidity and market interest, which makes executing transactions easier and less prone to slippage.
            """)

        # --- TAB 3: FUNDAMENTALS & COMPANY PROFILE ---
        with tab_fundamentals:
            st.subheader("Fundamental Health Metrics")
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Market Cap", stock_feat.get('market_cap', 'N/A'))
            f2.metric("Debt / Equity", f"{stock_feat.get('debt_to_equity', 0):.2f}")
            f3.metric("Debt / Assets", f"{stock_feat.get('debt_to_assets', 0):.2f}")
            f4.metric("Cash Ratio", f"{stock_feat.get('cash_ratio', 0):.2f}")
            
            st.divider()
            
            st.subheader("Company Profile Details")
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(f"**Industry:** {stock_feat.get('industry', 'N/A')}")
                st.markdown(f"**Sector:** {stock_feat.get('sector', 'N/A')}")
                st.markdown(f"**Ticker Symbol:** {stock_feat.get('ticker', 'N/A')}")
            with p_col2:
                st.markdown(f"**Exchange:** {stock_feat.get('exchange', 'N/A')}")
                st.markdown(f"**Country:** {stock_feat.get('country', 'India')}")
                st.markdown(f"**Status:** {'Active 🟢' if stock_feat.get('is_active', True) else 'Inactive 🔴'}")
            
            st.divider()
            describe_term("Key Fundamentals", """
            - **Market Cap**: Total market value of a company's outstanding shares.
            - **Debt to Equity**: Compares total liabilities to shareholder equity. High values suggest more debt-reliant growth.
            - **Debt to Assets**: Measures the percentage of assets financed by debt. Highlights leverage and capital structural risks.
            - **Cash Ratio**: Measures ability to pay short-term debt using only cash and cash equivalents.
            """)

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