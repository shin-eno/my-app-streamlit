import streamlit as st
import requests

st.title("🧾 レシート画像一括登録")
st.write("カテゴリを選択し、レシート画像をアップロードしてDBへ登録します。")

# =========================================================
# 【修正】DBからカテゴリ一覧を動的に取得する処理
# =========================================================
@st.cache_data(ttl=60)  # 頻繁にDBにアクセスするのを防ぐため、1分間キャッシュします
def load_categories_from_db():
    try:
        res = requests.get("http://backend:5000/api/categories")
        if res.status_code == 200:
            # 成功すると [{"id": 1, "name": "食費"}, ...] のようなリストが返ります
            return res.json()
    except Exception as e:
        st.error(f"カテゴリの取得に失敗しました: {e}")
    return []

# カテゴリデータの読み込み
db_categories = load_categories_from_db()

if db_categories:
    # セレクトボックスに表示する「名前」のリストを作成
    category_names = [cat['name'] for cat in db_categories]
    selected_category_name = st.selectbox("カテゴリを選択してください", category_names)
    
    # 選択された名前から、対応する「id」を見つけ出す
    category_id = next(cat['id'] for cat in db_categories if cat['name'] == selected_category_name)
else:
    # 万が一DBから取得できなかった場合のセーフティ
    st.warning("DBからカテゴリデータを取得できませんでした。")
    category_id = None

# =========================================================

# 入力方法の選択
upload_type = st.radio("入力方法を選択してください", ["ファイルから選択", "カメラで撮影"])

uploaded_file = None
if upload_type == "ファイルから選択":
    uploaded_file = st.file_uploader("レシート画像を選択してください", type=["png", "jpg", "jpeg"])
else:
    uploaded_file = st.camera_input("レシートを正面から撮影してください")

# 登録処理
if uploaded_file is not None and category_id is not None:
    st.image(uploaded_file, caption="選択されたレシート", use_container_width=True)
    
    if st.button("DBにレシート画像を登録", type="primary", width="stretch"):
        with st.spinner("画像をDBに保存中..."):
            
            files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {'category_id': category_id}
            
            try:
                res = requests.post("http://backend:5000/api/receipts/upload", files=files, data=data)
                if res.status_code == 200:
                    st.success("🎉 アップロードが完了しました。解析待ちです。")
                else:
                    error_msg = res.json().get("message", "サーバーエラー")
                    st.error(f"登録に失敗しました: {error_msg}")
            except Exception as e:
                st.error(f"バックエンドに接続できませんでした: {e}")