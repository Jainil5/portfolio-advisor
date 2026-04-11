import streamlit as st
import pandas as pd
import os
from helper_functions import get_current_price_by_name

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
    # === 2. THEMATIC METRIC DISPLAY ===
    stock_feat = features_df[features_df["stock_id"] == selected_id].iloc[0]
    
    # --- SECTION A: MARKET CONTEXT & PROFILE ---
    st.markdown("### 🏢 Company Profile")
    prof_c1, prof_c2, prof_c3, prof_c4 = st.columns(4)
    prof_c1.metric("Ticker", stock_feat.get('ticker', 'N/A'))
    prof_c2.metric("Sector", stock_feat.get('sector', 'N/A'))
    prof_c3.metric("Industry", stock_feat.get('industry', 'N/A'))
    prof_c4.metric("Market Cap", stock_feat.get('market_cap', 'N/A'))
    st.write("")

    # --- SECTION B: PRICE DYNAMICS ---
    st.markdown("### 📊 Price Dynamics")
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    
    cp = get_current_price_by_name(stock_feat['company_name'])
    if cp is None:
        cp = stock_feat.get('current_price', 0)
        
    dr = stock_feat.get('daily_return', 0)
    r1c1.metric("Current Price", f"₹{cp:,.2f}", f"{dr:.2f}%")
    r1c2.metric("52-Week High", f"₹{stock_feat.get('52w_high', 0):,.2f}")
    r1c3.metric("52-Week Low", f"₹{stock_feat.get('52w_low', 0):,.2f}")
    r1c4.metric("20-Day MA", f"₹{stock_feat.get('ma20', 0):,.2f}")
    r1c5.metric("50-Day MA", f"₹{stock_feat.get('ma50', 0):,.2f}")
    
    # --- SECTION C: PERFORMANCE & RETURNS ---
    st.markdown("### 💹 Performance Dashboard")
    perf_c1, perf_c2, perf_c3, perf_c4 = st.columns(4)
    perf_c1.metric("7-Day Return", f"{stock_feat.get('return_7d', 0):.2f}%")
    perf_c2.metric("30-Day Return", f"{stock_feat.get('return_30d', 0):.2f}%")
    perf_c3.metric("180-Day Return", f"{stock_feat.get('return_180d', 0):.2f}%")
    
    trend_val = stock_feat.get('trend', 'Neutral')
    trend_color = "🟢" if trend_val == "Bullish" else "🔴"
    perf_c4.markdown(f"**Current Trend**<br/><div style='font-size:20px'>{trend_color} {trend_val}</div>", unsafe_allow_html=True)
    st.write("")

    # --- SECTION D: VOLUME & LIQUIDITY ---
    st.markdown("### 🌊 Volume & Liquidity")
    vol_c1, vol_c2, vol_c3 = st.columns(3)
    vol_c1.metric("Avg Volume (7d)", f"{stock_feat.get('avg_volume_7d', 0):,.0f}")
    vol_c2.metric("Avg Volume (30d)", f"{stock_feat.get('avg_volume_30d', 0):,.0f}")
    vol_c3.metric("Avg Volume (180d)", f"{stock_feat.get('avg_volume_180d', 0):,.0f}")
    st.write("")

    # --- SECTION E: RISK & FUNDAMENTALS ---
    st.markdown("### ⚖️ Risk & Fundamental Health")
    risk_c1, risk_c2, risk_c3, risk_c4 = st.columns(4)
    risk_c1.metric("Volatility (30d)", f"{stock_feat.get('volatility_30d', 0):.2f}%")
    risk_c2.metric("Volatility (180d)", f"{stock_feat.get('volatility_180d', 0):.2f}%")
    risk_c3.metric("Debt to Equity", f"{stock_feat.get('debt_to_equity', 0):.2f}")
    risk_c4.metric("Cash Ratio", f"{stock_feat.get('cash_ratio', 0):.2f}")
    
    # Extra fundamental row
    fund_c1, fund_c2, fund_c3 = st.columns(3)
    fund_c1.metric("Debt to Assets", f"{stock_feat.get('debt_to_assets', 0):.2f}")
    st.write("")

    st.divider()

    # === 3. ANALYSIS & VISUALIZATION ===
    st.subheader("🤖 AI Analysis & Visualization")
    score = stock_feat.get("score", 0)
    
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.write(f"#### {stock_feat['company_name']} Price History")
        
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
                st.area_chart(price_df['Close'])
        else:
            st.warning("Price history data not found for this stock.")
            
    with exp_col2:
        st.write("#### Advisor Outlook")
        if score >= 3:
            st.success(f"**Overall Rating: STRONG** (Score: {score:.2f})")
            st.write("This stock shows exceptional strength across multiple horizons. High technical momentum combined with stable health makes it a top pick.")
        elif score >= 1.5:
            st.info(f"**Overall Rating: MODERATE** (Score: {score:.2f})")
            st.write("Mixed signals here. While fundamentals may be stable, momentum is either cooling or hasn't fully picked up yet.")
        else:
            st.error(f"**Overall Rating: WEAK** (Score: {score:.2f})")
            st.write("High risk or poor momentum. Technical trends are significantly bearish or volatility is outside acceptable ranges.")
           
        trend = stock_feat.get('trend', 'Neutral')
        if trend == "Bullish":
            st.write("🐂 **Bullish Trend:** Positive EMA/MA crossover indicates upward force.")
        else:
            st.write(" Bears currently dominate the price action for this stock.")
            
        volatility = stock_feat.get('volatility_30d', 0)
        if volatility > 40:
            st.write("⚠️ **High Volatility:** Caution - large swings are common.")
        else:
            st.write("✅ **Stable Volatility:** Price action is relatively predictable.")
