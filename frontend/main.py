import streamlit as st

# セッション状態の初期化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 1. 各ページの定義 ---
# ログイン画面を関数として定義（st.Pageの第一引数に関数を渡せます）
def login_screen():
    st.title("🔐 ログイン")
    u_id = st.text_input("ユーザーID", max_chars=5)
    u_pass = st.text_input("パスワード", type="password")
    if st.button("ログイン", type="primary"):
        # 本来はここにFlask APIへのリクエストを入れます
        # 今回はテスト用にIDが入力されていれば成功とします
        if u_id and u_pass:
            st.session_state.logged_in = True
            st.success("ログイン成功！")
            st.rerun()
        else:
            st.error("IDとパスワードを入力してください")

# 各ページオブジェクトの作成
login_page = st.Page(login_screen, title="ログイン", icon="🔐")
dashboard  = st.Page("views/1_Dashboard.py", title="ダッシュボード", icon="📊")
user_list  = st.Page("views/2_User_List.py", title="ユーザー管理", icon="👥")
user_reg   = st.Page("views/9_User_Registration.py", title="ユーザー登録", icon="👤")

# --- 2. ナビゲーションの構築 ---
if st.session_state.logged_in:
    # ログイン済み：業務メニューを表示
    pg = st.navigation({
        "メインメニュー": [dashboard],
        "管理設定": [user_list, user_reg]
    })
    # ログアウトボタンをサイドバーに配置
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()
else:
    # 未ログイン：ログインページのみを表示
    pg = st.navigation([login_page])

# --- 3. 最後に一回だけ実行 ---
pg.run()
