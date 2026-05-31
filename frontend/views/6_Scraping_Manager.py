import streamlit as st
import requests

st.title("📸 画像スクレイピング・コンバーター")
st.caption("指定したURLからWebP画像を抽出し、JPGに変換してZIP圧縮します。")

# 1. 画面から入力するフォームの作成
with st.form("scraping_form"):
    url = st.text_input(
        "スクレイピングするURL値", 
        placeholder="https://example.com/page"
    )
    download_name = st.text_input(
        "ファイル名（保存時の名称）", 
        placeholder="example_images"
    )
    
    # 2. 実行ボタン
    submit_button = st.form_submit_button("スクレイピングを実行", type="primary")

# 3. 実行ボタンが押された時の処理
if submit_button:
    if not url.strip() or not download_name.strip():
        st.error("❌ URLとファイル名の両方を入力してください。")
    else:
        # バックエンドでのバックグラウンド処理を明示するスピナーを表示
        with st.spinner("バックエンドで処理を実行中（DBログ記録 ➔ ダウンロード ➔ JPG変換 ➔ ZIP化）..."):
            try:
                # バックエンドのFlask APIへリクエストを送信
                response = requests.post(
                    "http://backend:5000/api/scraping/run",
                    json={
                        "url": url.strip(), 
                        "download_name": download_name.strip()
                    },
                    timeout=300  # 枚数が多い場合を想定しタイムアウトを5分に設定
                )
                
                # 正常・異常のステータスに応じたメッセージ出力
                if response.status_code == 200:
                    res_data = response.json()
                    st.success(f"🎉 完了: {res_data.get('message')}")
                    st.info(f"コンテナ内保存先: {res_data.get('file_path')}")
                else:
                    res_data = response.json()
                    st.error(f"❌ 処理が失敗判定となりました: {res_data.get('message')}")
                    
            except requests.exceptions.Timeout:
                st.error("❌ タイムアウトが発生しました。画像の枚数が非常に多い可能性があります。バックエンドのログを確認してください。")
            except Exception as e:
                st.error(f"❌ バックエンドとの通信エラー: {e}")