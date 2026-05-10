import streamlit as st
import requests

st.title("📊 ダッシュボード")

if st.button("最新ステータスを確認"):
    # Flaskへの通信も各ページで実施可能
    res = requests.get("http://backend:5000/api/db-check")
    st.json(res.json())
