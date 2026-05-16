import streamlit as st
import requests

st.title("🔄 パスワード再設定")

# 1. URLパラメータからトークンを取得
query_params = st.query_params
token = query_params.get("token")

# トークンがURLにない場合は処理を中断
if not token:
    st.error("有効なトークンが見つかりません。メールのリンクから再度アクセスしてください。")
    st.stop()

# 2. パスワード入力フォームの構築
with st.form("reset_form"):
    new_pass = st.text_input("新しいパスワード", type="password")
    confirm_pass = st.text_input("新しいパスワード（確認用）", type="password")
    
    # フォーム送信ボタン
    submit = st.form_submit_button("パスワードを更新", width='stretch')

# 3. ボタンが押されたときの処理
if submit:
    if not new_pass or not confirm_pass:
        st.warning("すべての項目を入力してください。")
        
    elif new_pass != confirm_pass:
        st.error("新しいパスワードが一致しません。")
        
    elif len(new_pass) < 4:  # 簡易的なバリデーション（文字数制限など）
        st.error("パスワードは4文字以上で入力してください。")
        
    else:
        # バックエンドへの送信データ（ペイロード）を作成
        payload = {
            "token": token,
            "new_password": new_pass
        }
        
        try:
            res = requests.post("http://backend:5000/api/auth/reset-password", json=payload)
            
            if res.status_code == 200:
                # 成功した場合、セッション状態にフラグを立てる
                st.session_state.password_reset_success = True

                # 1. URLのパラメータ (?token=...) を綺麗に削除
                st.query_params.clear()
                
                # 2. 【変更ポイント】エラーを起こしやすい switch_page の代わりに
                # 内部状態をリロードして、main.py の初期状態（通常のログイン画面）へ安全に戻します
                st.rerun() 
                
            else:
                error_msg = res.json().get("message", "不明なエラー")
                st.error(f"更新に失敗しました: {error_msg}")
                
        except Exception as e:
            st.error(f"システムエラー（バックエンドに接続できません）: {e}")