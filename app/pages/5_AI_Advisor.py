import streamlit as st
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.stock_agent import query_stock_info

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="centered")
st.title("🤖 AI Portfolio Advisor")

st.markdown("""
Welcome to the AI Advisor. I have access to the **Master Dataset** covering technical features, latest fundamentals, and top recommendations.
Ask me anything about stocks!
""")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Quick action buttons for demo queries
demo_q = None
if len(st.session_state.messages) == 0:
    st.markdown("### Try asking:")
    col1, col2, col3,col4 = st.columns(4)
    if col1.button("Compare Adani ensol and NTPC"):
        demo_q = "Compare Adani ensol and NTPC"
    if col2.button("Why is Vedanta growing?"):
        demo_q = "Why is Vedanta growing?"
    if col3.button("Recommend me some stocks"):
        demo_q = "Recommend me some stocks to buy"
    if col4.button("Should I buy Reliance?"):
        demo_q = "Should I buy Reliance?"    
    st.divider()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
prompt = st.chat_input("Ask about a stock or your portfolio...")
user_q = prompt or demo_q

if user_q:
    # Display user message in chat message container
    st.chat_message("user").markdown(user_q)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_q})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Analyzing market data..."):
            response = query_stock_info(user_q)
        st.markdown(response)
        
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
