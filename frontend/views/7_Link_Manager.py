import streamlit as st
import requests
import pandas as pd
import math
import json
import os

st.set_page_config(page_title="リンク集管理", layout="wide")
st.title("🔗 リンク集マスタ")

# バックエンドAPIベースURL
API_URL = "http://backend:5000/api/links"

# ==========================================
# ⚙️ 外部設定ファイル (config.json) の読み込み
# ==========================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
items_per_page = 10  # デフォルト値（読み込み失敗時のセーフティ）

try:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            items_per_page = config_data.get("link_manager", {}).get("items_per_page", 10)
except Exception as e:
    st.sidebar.warning(f"設定ファイルの読み込みに失敗したため、デフォルト値(10件)で動作します: {e}")

# セッション状態からログインユーザーの管理者情報を取得
user_info = st.session_state.get('user_info', {})
is_admin = user_info.get('is_admin', False)

# セッション状態の初期化
if 'edit_target' not in st.session_state:
    st.session_state.edit_target = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# ==========================================
# 1. 📂 登録リンク一覧（検索・ページング・独立スクロール付き）
# ==========================================
st.subheader("📋 登録リンク一覧")

try:
    response = requests.get(API_URL)
    if response.status_code == 200:
        link_data = response.json()
        
        if link_data:
            # 検索窓
            search_query = st.text_input("🔍 リンク集からキーワードで絞り込み (サイト名やカテゴリなど)", "")
            
            # データの絞り込み
            filtered_links = []
            for l in link_data:
                if search_query:
                    q = search_query.lower()
                    if (q not in l['site_name'].lower()) and (q not in (l['category'] or '').lower()) and (q not in (l['description'] or '').lower()):
                        continue
                filtered_links.append(l)

            total_items = len(filtered_links)

            if total_items > 0:
                # ページング計算
                total_pages = math.ceil(total_items / items_per_page)
                if st.session_state.current_page > total_pages:
                    st.session_state.current_page = 1
                
                current_page = st.session_state.current_page
                start_idx = (current_page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                page_items = filtered_links[start_idx:end_idx]

                st.markdown(f"**表示件数: {items_per_page}件 / ページ** (config.json で管理中)")
                st.divider()

                # --- 📜 Streamlit標準機能による独立スクロールエリア ---
                # 指定した高さ（400px）を超えると自動でコンテナ内だけが独立スクロールします。
                # HTMLタグの破綻を防ぎ、PC/スマホを問わずレイアウトが崩れません。
                with st.container(height=400, border=True):
                    for idx, l in enumerate(page_items):
                        # サイト名を別タブリンク化
                        clickable_site = f'<a href="{l["url"]}" target="_blank" rel="noopener noreferrer" style="font-size: 1.1rem; font-weight: bold; text-decoration: none;">🔗 {l["site_name"]}</a>'
                        
                        col_main, col_btn = st.columns([7, 3])  # スマホ幅を考慮してボタン側の比率を調整
                        with col_main:
                            st.write(clickable_site, unsafe_allow_html=True)
                            meta_info = f"`カテゴリ: {l['category'] or '-'}` ｜ `表示順: {l['display_order']}`"
                            st.caption(meta_info)
                            if l['description']:
                                st.info(l['description'])
                        
                        with col_btn:
                            if is_admin:
                                if st.button("⚙️ 編集選択", key=f"sel_{l['id']}_{idx}", use_container_width=True):
                                    st.session_state.edit_target = l
                                    st.success(f"「{l['site_name']}」を選択しました。下の編集フォームへ進んでください。")
                                    st.rerun()
                        
                        # 最後の要素以外に区切り線をいれる
                        if l != page_items[-1]:
                            st.divider()
                
                # --- 🕹️ ページング操作UI ---
                page_cols = st.columns([1, 2, 1])
                with page_cols[0]:
                    if current_page > 1:
                        if st.button("⬅️ 前へ", use_container_width=True):
                            st.session_state.current_page -= 1
                            st.rerun()
                with page_cols[1]:
                    st.markdown(
                        f"<div style='text-align: center; font-weight: bold; padding-top: 5px;'>"
                        f"{current_page} / {total_pages} ページ （全 {total_items} 件）"
                        f"</div>", 
                        unsafe_allow_html=True
                    )
                with page_cols[2]:
                    if current_page < total_pages:
                        if st.button("次へ ➡️", use_container_width=True):
                            st.session_state.current_page += 1
                            st.rerun()

            else:
                st.info("絞り込み条件に一致するリンクはありません。")
        else:
            st.info("登録されているリンクはありません。")
            link_data = []
    else:
        st.error("データの取得に失敗しました。")
        link_data = []
except Exception as e:
    st.error(f"通信エラー: {e}")
    link_data = []

st.divider()

# ==========================================
# 2. 🛠️ 管理者専用：追加・編集・削除エリア
# ==========================================
if is_admin:
    st.subheader("⚙️ リンク集の管理操作（管理者専用）")
    tab1, tab2 = st.tabs(["➕ 新規登録", "✏️ 選択中のリンクを編集・削除"])

    # --- タブ1：新規登録 ---
    with tab1:
        with st.form("add_link_form", clear_on_submit=True):
            site_name = st.text_input("サイト名")
            url = st.text_input("URL値 (必須)", placeholder="https://...")
            category = st.text_input("カテゴリ")
            display_order = st.number_input("表示順", min_value=1, value=10, step=1)
            description = st.text_area("説明")
            
            if st.form_submit_button("リンクを新規登録", type="primary"):
                if not site_name.strip() or not url.strip():
                    st.error("サイト名とURL値は必須項目です。")
                else:
                    payload = {
                        "site_name": site_name.strip(), "url": url.strip(), 
                        "category": category.strip(), "display_order": display_order, 
                        "description": description.strip()
                    }
                    res = requests.post(API_URL, json=payload)
                    if res.status_code == 201:
                        st.success("登録が完了しました。")
                        st.rerun()
                    else:
                        st.error("登録に失敗しました。")

    # --- タブ2：編集・削除 ---
    with tab2:
        target = st.session_state.edit_target
        
        if target:
            st.warning(f"現在 **[ ID: {target['id']} | {target['site_name']} ]** を編集選択中。")
            with st.form("edit_and_delete_form"):
                e_site_name = st.text_input("サイト名", value=target['site_name'])
                e_url = st.text_input("URL値", value=target['url'])
                e_category = st.text_input("カテゴリ", value=target['category'])
                e_display_order = st.number_input("表示順", min_value=1, value=target['display_order'], step=1)
                e_description = st.text_area("説明", value=target['description'])
                
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_edit = st.form_submit_button("✏️ 変更内容を保存する", type="primary")
                with col_btn2:
                    submit_del = st.form_submit_button("🗑️ このリンクを削除（論理削除）")
                
                if submit_edit:
                    if not e_site_name.strip() or not e_url.strip():
                        st.error("サイト名とURL値は必須項目です。")
                    else:
                        payload = {
                            "site_name": e_site_name.strip(), "url": e_url.strip(), 
                            "category": e_category.strip(), "display_order": e_display_order, 
                            "description": e_description.strip()
                        }
                        res = requests.put(f"{API_URL}/{target['id']}", json=payload)
                        if res.status_code == 200:
                            st.success("更新が完了しました。")
                            st.session_state.edit_target = None
                            st.rerun()
                        else:
                            st.error("更新に失敗しました。")
                            
                if submit_del:
                    res = requests.delete(f"{API_URL}/{target['id']}")
                    if res.status_code == 200:
                        st.success("論理削除が完了しました。")
                        st.session_state.edit_target = None
                        st.rerun()
                    else:
                        st.error("削除処理に失敗しました。")
                        
            if st.button("❌ 編集をキャンセル"):
                st.session_state.edit_target = None
                st.rerun()
        else:
            st.info("💡 上の一覧テーブルから、編集したいリンクの【⚙️ 選択する】ボタンを押してください。ここにデータがロードされます。")
else:
    st.caption("ℹ️ リンクの追加・変更・削除操作は、管理者アカウントのみに制限されています。")