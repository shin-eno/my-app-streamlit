import streamlit as st
import requests

# 1. セッション状態の初期化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'user_pages' not in st.session_state:
    st.session_state.user_pages = []

#
# 2. ログイン画面の定義
#
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

    st.markdown("---") # 区切り線
    if st.button("パスワードを忘れた方はこちら", width='stretch'):
        show_forgot_password_dialog()

    pass


#
# メールアドレス入力用のダイアログを表示する関数
#
@st.dialog("パスワード再設定の請求")
def show_forgot_password_dialog():
    st.write("登録されているユーザーIDを入力してください。再設定用のリンクをメールで送信します。")
    target_id = st.text_input("ユーザーID (5桁)")
    
    if st.button("再設定メールを送信", width='stretch'):
        if target_id:
            try:
                # バックエンドの forgot-password APIを叩く
                res = requests.post("http://backend:5000/api/auth/forgot-password", 
                                    json={"user_id": target_id})
                if res.status_code == 200:
                    st.success("Mailpit（または登録メール）を確認してください。")
                else:
                    st.error("送信に失敗しました。IDが正しいか確認してください。")
            except Exception as e:
                st.error(f"システムエラー: {e}")
        else:
            st.warning("ユーザーIDを入力してください。")

    pass

#
# 3. ページオブジェクトの構築（メインロジック）
#

# ログインページオブジェクト
login_page = st.Page(login_screen, title="ログイン", icon="🔐")

# 再設定ページオブジェクトの定義
reset_page = st.Page("views/4_Reset_Password.py", title="パスワード再設定")

# URLからトークンを正しく取得する
token = st.query_params.get("token")


# =========================================================
# 4. ナビゲーションの動的制御
# =========================================================
if st.session_state.logged_in:
    # --- 【パターンA】ログイン済みの時 ---
    menu_structure = {}
    for p in st.session_state.user_pages:
        section = p.get('section_name') or "メイン"
        # ファイルパス、タイトル、アイコンをDBの設定から読み込んで動的に生成
        page_obj = st.Page(p['file_path'], title=p['page_title'], icon=p['icon'])
        if section not in menu_structure:
            menu_structure[section] = []
        menu_structure[section].append(page_obj)
        
    pg = st.navigation(menu_structure)
    
    # 共通サイドバーにログアウトボタンを配置
    if st.sidebar.button("ログアウト", width='stretch'):
        st.session_state.logged_in = False
        st.session_state.user_info = {}
        st.session_state.user_pages = []
        st.rerun()

elif token:
    # --- 【パターンB】未ログインだがメールのリンク（トークンあり）からアクセスした時 ---
    # ★ここが最重要です。これによってStreamlitに公式ルートとして再設定画面を認めさせます。
    pg = st.navigation([reset_page])

else:
    # --- 【パターンC】通常のアクセス（未ログイン・トークンなし）の時 ---
    pg = st.navigation([login_page])


# =========================================================
# 5. アプリケーションの実行
# =========================================================
# ★必ずインデントをつけずに（一番左端の階層で）最後に実行します
pg.run()

# ★ pg.run() の後にトースト表示処理を追加します
if st.session_state.get("password_reset_success"):
    # トースト通知を表示（アイコンも指定できます）
    st.toast("パスワードを正常に更新しました！新しいパスワードでログインしてください。", icon="🎉")
    
    # 一度表示したら、次回リロード時に出ないようにフラグを消去
    del st.session_state.password_reset_success
