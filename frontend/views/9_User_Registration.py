import streamlit as st
import requests

st.set_page_config(page_title="ユーザー登録")
st.title("👤 新規ユーザー登録")

# 入力フォーム
with st.form("registration_form"):
    u_id = st.text_input("ユーザーID (5桁以内)", max_chars=5)
    u_name = st.text_input("氏名")
    u_mail = st.text_input("メールアドレス")
    u_pass = st.text_input("パスワード", type="password")
    u_pass_confirm = st.text_input("パスワード（確認用）", type="password")
    
    submit = st.form_submit_button("登録実行")

if submit:
    print("test")
    # 簡単なバリデーション
    if not (u_id and u_name and u_mail and u_pass):
        st.error("すべての項目を入力してください")
    elif u_pass != u_pass_confirm:
        st.error("パスワードが一致しません")
    else:
        # バックエンドAPIへ送信
        payload = {
            "user_id": u_id,
            "user_name": u_name,
            "mail_address": u_mail,
            "password": u_pass
        }
        print("test")
        try:
            res = requests.post("http://backend:5000/api/register", json=payload)
            print(res.status_code)
            if res.status_code == 201:
                st.success("登録に成功しました！ログイン画面へ移動してください。")
            else:
                st.error(f"登録失敗: {res.json().get('error')}")
        except Exception as e:
            st.error(f"通信エラーが発生しました: {e}")
