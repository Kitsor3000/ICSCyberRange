import streamlit as st

st.title("ICSCyberRange Dashboard")

st.write("System is running")

if st.button("Test Attack"):
    st.error("Attack simulated!")