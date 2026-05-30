import os
import sys
import logging
from flask import Flask

# 新しいBlueprint（ルーティング定義）をインポート
from routes.auth_routes import auth_bp
from routes.receipt_routes import receipt_bp

# -------------------------------------------------------------
# 📄 ロギング（ログ出力）の一括初期設定
# -------------------------------------------------------------
def setup_logging():
    # 環境変数から現在の環境（development / production）を取得（デフォルトは production）
    flask_env = os.environ.get('FLASK_ENV', 'dev')
    
    # 環境に応じてログレベルを動的に決定
    if flask_env == 'dev':
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # ログの出力フォーマットを設定
    # [日時] [ログレベル] [実行されたファイル名:行番号] メッセージ
    log_format = '[%(asctime)s] %(levelname)s in %(filename)s:%(lineno)d: %(message)s'
    
    # 既存のFlaskのデフォルトハンドラをクリアして上書きできるようにする
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout) # Dockerのログ（stdout）に標準出力する
        ]
    )

# Flaskアプリ起動前にログを設定
setup_logging()

app = Flask(__name__)

# 起動時ログ（正しくロギングが動いているかの確認用）
logger = logging.getLogger(__name__)
logger.info(f"バックエンドサーバーを起動しました (環境: {os.environ.get('FLASK_ENV', 'production')})")

# -------------------------------------------------------------
# 起動時チェック: コンテナの環境変数が揃っているかを厳格に担保
# -------------------------------------------------------------
REQUIRED_ENV_VARS = ['DRIVE_FOLDER_ID', 'GOOGLE_CREDENTIALS_PATH', 'GOOGLE_TOKEN_PATH', 'GEMINI_API_KEY']
for var in REQUIRED_ENV_VARS:
    if not os.environ.get(var):
        print(f"【CRITICAL ERROR】必須環境変数 '{var}' が設定されていません。", file=sys.stderr)
        raise ValueError(f"Missing required environment variable: {var}")

# -------------------------------------------------------------
# プラグイン（Blueprint）の登録
# -------------------------------------------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(receipt_bp)
