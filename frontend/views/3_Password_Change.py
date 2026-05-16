import streamlit as st
import requests

st.title("🔑 パスワード変更")

if not st.session_state.get('logged_in'):
    st.warning("ログインが必要です。")
    st.stop()

with st.form("password_change_form"):
    current_pass = st.text_input("現在のパスワード", type="password")
    new_pass = st.text_input("新しいパスワード", type="password")
    confirm_pass = st.text_input("新しいパスワード（確認用）", type="password")
    
    submit = st.form_submit_button("パスワードを更新", width='stretch')

if submit:
    if new_pass != confirm_pass:
        st.error("新しいパスワードが一致しません。")
    elif len(new_pass) < 4: # 簡易的なバリデーション
        st.error("パスワードは4文字以上で入力してください。")
    else:
        payload = {
            "user_id": st.session_state.user_info['user_id'],
            "current_password": current_pass,
            "new_password": new_pass
        }
        try:
            res = requests.post("http://backend:5000/api/users/change-password", json=payload)
            if res.status_code == 200:
                st.success("パスワードを正常に変更しました。")
            else:
                st.error(f"変更に失敗しました: {res.json().get('message')}")
        except Exception as e:
            st.error(f"システムエラー: {e}")
