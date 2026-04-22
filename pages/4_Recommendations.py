import streamlit as st
import pandas as pd
import os
from helper_functions import get_current_price_by_name
from stock_agent import query_stock_info

st.set_page_config(page_title="Recommendations", page_icon="⭐", layout="wide")
st.title("⭐ Top Stock Recommendations")

RECOMMENDATIONS_FILE = "data/recommendations.csv"

@st.cache_data
def get_recommendations():
    if not os.path.exists(RECOMMENDATIONS_FILE):
        return pd.DataFrame()
        
    return pd.read_csv(RECOMMENDATIONS_FILE)

recommended_df = get_recommendations()

if recommended_df.empty:
    st.info("No recommendations available at this time. Run the backend pipeline.")
    st.stop()

st.markdown("Based on our advanced AI scoring system (incorporating momentum, volatility, and trend), here are the top picks for you to consider.")

for idx, row in recommended_df.iterrows():
    with st.container():
        rec_label = row.get("recommendation", "BUY")
        st.subheader(f"{row['company_name']} - {rec_label} (Score: {row['score']:.2f})")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        # Use fresh price lookup
        curr_p = get_current_price_by_name(row['company_name'])
        if curr_p is None:
            curr_p = row.get('current_price', 0)
            
        c1.metric("Current Price", f"₹{curr_p:.2f}")
        c2.metric("30d Return", f"{row.get('return_30d', 0):.2f}%")
        c3.metric("180d Return", f"{row.get('return_180d', 0):.2f}%")
        c4.metric("Volatility", f"{row.get('volatility_30d', 0):.2f}%")
        c5.markdown(f"**Trend:** {'🟢 Bullish' if row.get('trend') == 'Bullish' else '🔴 Bearish'}")
        
        explanation = row.get("explanation", "")
        if pd.isna(explanation) or not explanation:
            explanation = "Solid overall quantitative metrics across multiple horizons."
            
        # Format explanation nicely if it has newlines
        formatted_exp = explanation.replace('\n', '\n> ')
        st.markdown(f"> **Why we recommend it:**\n> {formatted_exp}")
        st.divider()

# --- FIXED AGENT QUESTION BAR ---
st.markdown("<br/><br/><br/>", unsafe_allow_html=True) # Spacer
with st.container():
    st.markdown("---")
    st.write("### 🤖 Portfolio Advisor Agent")
    q_col, s_col = st.columns([5, 1])
    with q_col:
        user_query = st.text_input("Ask me anything about these recommendations...", 
                                  placeholder="e.g., Why is Adani recommended over Reliance?", 
                                  key="rec_agent_input",
                                  label_visibility="collapsed")
    with s_col:
        send_pressed = st.button("Send", width='stretch', key="rec_agent_send")
    
    if send_pressed and user_query:
        with st.chat_message("user"):
            st.markdown(user_query)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing recommendations..."):
                ans = query_stock_info(user_query)
                st.markdown(ans)

