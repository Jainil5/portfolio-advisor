import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Stock Analysis", page_icon="📈", layout="wide")

FEATURES_FILE = "data/features.csv"
PRICE_DIR = "data/prices"
STOCKS_FILE = "data/stocks.csv"



@st.cache_data
def load_data():
    features = pd.read_csv(FEATURES_FILE) if os.path.exists(FEATURES_FILE) else pd.DataFrame()
    stocks = pd.read_csv(STOCKS_FILE) if os.path.exists(STOCKS_FILE) else pd.DataFrame()
    return features, stocks



features_df, stocks_df = load_data()

if features_df.empty or stocks_df.empty:
    st.warning("Insufficient data. Please run backend scripts to fetch stocks and generate features.")
    st.stop()

# 1. Select Stock
stock_map = dict(zip(features_df["stock_id"], features_df["company_name"]))
sorted_stock_ids = sorted(stock_map.keys(), key=lambda x: stock_map[x])


c1,c2 = st.columns(2)

with c1:
    st.title("📈 Stock Analysis")
with c2:
    selected_id = st.selectbox("Select a stock to analyze:", options=sorted_stock_ids, format_func=lambda x: stock_map[x])

st.divider()    
if selected_id:
    # 2. Display Metrics
    stock_feat = features_df[features_df["stock_id"] == selected_id].iloc[0]
    
    # Price Overview Row
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    
    cp = stock_feat.get('current_price', 0)
    dr = stock_feat.get('daily_return', 0)
    r1c1.metric("Current Price", f"₹{cp:,.2f}", f"{dr:.2f}%")
    r1c2.metric("52-Week High", f"₹{stock_feat.get('52w_high', 0):,.2f}")
    r1c3.metric("52-Week Low", f"₹{stock_feat.get('52w_low', 0):,.2f}")
    r1c4.metric("50-Day MA", f"₹{stock_feat.get('ma50', 0):,.2f}")
    
    trend_color = "🟢" if stock_feat.get("trend") == "Bullish" else "🔴"
    r1c5.markdown(f"**Trend**<br/><div style='font-size:24px'>{trend_color} {stock_feat.get('trend', 'Neutral')}</div>", unsafe_allow_html=True)

    st.write("") # Spacer

    # Performance Row
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.metric("7d Return", f"{stock_feat.get('return_7d', 0):.2f}%")
    r2c2.metric("30d Return", f"{stock_feat.get('return_30d', 0):.2f}%")
    r2c3.metric("180d Return", f"{stock_feat.get('return_180d', 0):.2f}%")
    r2c4.metric("Volatility (30d)", f"{stock_feat.get('volatility_30d', 0):.2f}%")
    
    st.write("") # Spacer

    # Fundamentals Row
    st.markdown("#### Key Fundamentals")
    f1, f2, f3 = st.columns(3)
    f1.metric("Debt to Equity", f"{stock_feat.get('debt_to_equity', 0):.2f}")
    f2.metric("Cash Ratio", f"{stock_feat.get('cash_ratio', 0):.2f}")
    f3.metric("Company Sector", f"{stock_feat.get('sector', 'N/A')}")
    
    st.divider()

    
    # 4. Display Explanation
    st.subheader("AI Analysis & Explanation")
    score = stock_feat.get("score", 0)
    trend = stock_feat.get("trend", "Neutral")
    volatility = stock_feat.get("volatility_30d", 0)
    
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
         # 3. Display Price Chart
        st.subheader(f"{stock_feat['company_name']} Price Chart")
        
        # Needs a bit of string matching to find the right file in PRICE_DIR
        price_file = None
        for f in os.listdir(PRICE_DIR):
            if f.startswith(f"{selected_id}_"):
                price_file = os.path.join(PRICE_DIR, f)
                break
                
        if price_file and os.path.exists(price_file):
            price_df = pd.read_csv(price_file)
            if "Date" in price_df.columns and "Close" in price_df.columns:
                price_df['Date'] = pd.to_datetime(price_df['Date'], utc=True, errors='coerce')
                price_df.set_index('Date', inplace=True)
                st.line_chart(price_df['Close'])
        else:
            st.warning("Price history data not found for this stock.")
            
    with exp_col2:
        if score >= 3:
            st.success(f"**Overall Rating: STRONG** (Score: {score:.2f})")
            st.write("This stock shows strong momentum based on outperforming algorithms. Highly recommended to maintain in portfolio or consider buying.")
        elif score >= 1.5:
            st.info(f"**Overall Rating: MODERATE** (Score: {score:.2f})")
            st.write("This stock has average performance. It's safe but don't expect explosive short-term growth.")
        else:
            st.error(f"**Overall Rating: WEAK** (Score: {score:.2f})")
            st.write("Poor momentum and scoring. Consider taking profits if you own it or look for better opportunities.")
           
        if trend == "Bullish":
            st.write("🐂 **Bullish Trend:** The stock is trading above its 50-day moving average, a strong positive indicator.")
        else:
            st.write("🐻 **Bearish Trend:** The stock is trading below short-term averages, indicating selling pressure.")
            
        if volatility > 40:
            st.write("⚠️ **High Volatility:** Prices fluctuate wildly. Keep position sizes manageable.")
        else:
            st.write("✅ **Stable Volatility:** Risk of massive daily swing is relatively low.")
