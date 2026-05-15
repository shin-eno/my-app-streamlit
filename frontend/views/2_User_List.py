import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="ユーザー一覧", layout="wide")
st.title("👥 ユーザー管理一覧")

try:
    response = requests.get("http://backend:5000/api/users")
    if response.status_code == 200:
        user_data = response.json()
        
        if user_data:
            # 1. 取得した生データをそのままDataFrameにする
            df = pd.DataFrame(user_data)
            
            # 2. カラム名を日本語にマッピングする（辞書形式で指定）
            # これにより、キー名が一致するものだけが正確に置換されます
            rename_dict = {
                "id": "ID",
                "user_id": "ユーザーID",
                "user_name": "氏名",
                "mail_address": "メール",
                "administrator_flg": "管理者",
                "delete_flg": "削除フラグ",
                "created_at": "作成日"
            }
            
            # 3. 指定したカラムだけを、指定した順番で抽出
            # カラム名が間違っている場合に備え、存在する列のみ選択
            target_columns = [col for col in rename_dict.keys() if col in df.columns]
            df = df[target_columns]
            
            # 4. 日本語名に一括変換
            df = df.rename(columns=rename_dict)
            
            # 表示
            st.dataframe(df, width='stretch')
            
            st.info(f"現在登録されている有効なユーザー数: {len(df)}名")
        else:
            st.write("登録されているユーザーはいません。")
    else:
        st.error(f"エラーが発生しました (Status: {response.status_code})")
except Exception as e:
    st.error(f"通信エラー: {e}")

if st.button("情報を更新"):
    st.rerun()

st.divider() # 区切り線
st.subheader("🗑️ ユーザーの削除")

col1, col2 = st.columns([3, 1])

with col1:
    target_id = st.text_input("削除したいユーザーIDを入力してください", max_chars=5)

with col2:
    st.write(" ") # 余白調整
    if st.button("削除実行", type="primary"):
        if target_id:
            try:
                res = requests.delete(f"http://backend:5000/api/users/{target_id}")
                if res.status_code == 200:
                    st.success(f"ユーザー {target_id} を削除しました")
                    st.rerun() # 画面を更新して一覧から消す
                else:
                    st.error(res.json().get("error"))
            except Exception as e:
                st.error(f"エラー: {e}")
        else:
            st.warning("IDを入力してください")
