import streamlit as st
import requests

# 1. セッション状態の初期化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'user_pages' not in st.session_state:
    st.session_state.user_pages = []

# 2. ログイン画面の定義
def login_screen():
    st.title("🔐 業務システム ログイン")
    u_id = st.text_input("ユーザーID", max_chars=5)
    u_pass = st.text_input("パスワード", type="password")
    
    if st.button("ログイン", type="primary", width='stretch'):
        try:
            res = requests.post("http://backend:5000/api/login", json={"user_id": u_id, "password": u_pass})
            if res.status_code == 200:
                data = res.json()
                
                # キーの存在チェックを行い、エラーを防ぐ[cite: 6, 8]
                if 'pages' in data:
                    st.session_state.logged_in = True
                    st.session_state.user_info = data.get('user', {})
                    st.session_state.user_pages = data['pages']
                    st.rerun()
                else:
                    # 'pages' が無い場合は詳細を表示
                    st.error(f"APIエラー: レスポンスに 'pages' が含まれていません。受信データ: {data}")
            else:
                st.error(f"認証に失敗しました。ステータスコード: {res.status_code}")
        except Exception as e:
            # ここで 'pages' という文字列のエラー（KeyError）が出ていたのを修正
            st.error(f"接続エラーまたはデータ処理エラー: {e}")

# 3. ページオブジェクトの構築
login_page = st.Page(login_screen, title="ログイン", icon="🔐")

if st.session_state.logged_in:
    menu_structure = {}
    
    if st.session_state.user_pages:
        for p in st.session_state.user_pages:
            section = p.get('section_name') or "メイン"
            # DBのデータに基づき構築
            page_obj = st.Page(p['file_path'], title=p['page_title'], icon=p['icon'])
            
            if section not in menu_structure:
                menu_structure[section] = []
            menu_structure[section].append(page_obj)
        
        pg = st.navigation(menu_structure)
    else:
        st.error("表示可能なページがありません。")
        if st.sidebar.button("ログイン画面に戻る", width='stretch'):
            st.session_state.logged_in = False
            st.rerun()
        pg = st.navigation([login_page])
else:
    pg = st.navigation([login_page])

# 4. 実行とログアウト処理
if st.session_state.logged_in:
    if st.sidebar.button("ログアウト", width='stretch'):
        st.session_state.logged_in = False
        st.session_state.user_info = {}
        st.session_state.user_pages = []
        st.rerun()

pg.run()