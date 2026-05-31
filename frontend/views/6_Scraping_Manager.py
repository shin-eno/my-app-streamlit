import streamlit as st
import requests
import pandas as pd

st.title("📸 画像スクレイピング・コンバーター (非同期対応版)")
st.caption("ボタンを押すと裏側で処理が実行されます。待たずに次のリクエストを送信可能です。")

# 1. 入力フォーム
with st.form("scraping_form", clear_on_submit=True):
    url = st.text_input(
        "スクレイピングするURL値", 
        placeholder="https://example.com/page"
    )
    download_name = st.text_input(
        "ファイル名（保存時の名称）", 
        placeholder="example_images"
    )
    submit_button = st.form_submit_button("スクレイピングを実行", type="primary")

# 2. 実行ボタン押下時の処理
if submit_button:
    if not url.strip() or not download_name.strip():
        st.error("❌ URLとファイル名の両方を入力してください。")
    else:
        try:
            # バックエンドへリクエストを送信（即座に応答が返ってくる）
            response = requests.post(
                "http://backend:5000/api/scraping/run",
                json={
                    "url": url.strip(), 
                    "download_name": download_name.strip()
                }
            )
            
            if response.status_code == 202:
                res_data = response.json()
                # 即座に受付完了メッセージを出す
                st.success(f"📥 受付完了: {res_data.get('message')} (ログID: {res_data.get('log_id')})")
            else:
                res_data = response.json()
                st.error(f"❌ リクエストが拒否されました: {res_data.get('message')}")
                
        except Exception as e:
            st.error(f"❌ バックエンドとの通信エラー: {e}")

st.divider() # 区切り線

# 3. 📄 過去10回分の履歴出力セクション
st.subheader("🕒 直近10回の実施結果履歴")

try:
    # 履歴取得APIを呼び出す
    history_res = requests.get("http://backend:5000/api/scraping/history")
    if history_res.status_code == 200:
        logs = history_res.json()
        
        if logs:
            # データを綺麗に表示するために DataFrame に変換
            df = pd.DataFrame(logs)
            
            # ステータスの表記を少しわかりやすく絵文字付きにするマッピング
            status_map = {
                "RUNNING": "⏳ 実行中 (RUNNING)",
                "SUCCESS": "✅ 成功 (SUCCESS)",
                "FAILED": "❌ 失敗 (FAILED)"
            }
            df['status'] = df['status'].map(status_map).fillna(df['status'])
            
            # 表示するカラム名と日本語のマッピング
            rename_dict = {
                "id": "ログID",
                "download_name": "ファイル名",
                "target_url": "対象URL",
                "status": "現在の状態",
                "error_message": "エラー内容",
                "created_at": "実行開始日時"
            }
            
            # 列の選別と日本語化
            target_columns = [col for col in rename_dict.keys() if col in df.columns]
            df = df[target_columns].rename(columns=rename_dict)
            
            # Streamlitのデータフレームコンポーネントで出力
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.info("過去の実行履歴はありません。")
    else:
        st.error("履歴データの取得に失敗しました。")
except Exception as e:
    st.error(f"履歴取得中に通信エラーが発生しました: {e}")

# 履歴を手動で最新にするためのリフレッシュボタン
if st.button("🔄 履歴を最新の情報に更新"):
    st.rerun()
