import streamlit as st
import requests
import pandas as pd

import os

st.set_page_config(page_title="メインシステム", layout="wide")

print(f"Current Directory: {os.getcwd()}")
print(f"Files in pages: {os.listdir('pages')}")

st.title("🚀 業務基盤システム")
st.sidebar.success("上のメニューから機能を選択してください")

st.write("""
### システム概要
このアプリは以下の構成で動作しています：
- **Frontend**: Streamlit (Python 3.13)
- **Backend**: Flask API
- **Database**: PostgreSQL
""")