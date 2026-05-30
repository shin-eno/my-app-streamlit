import os
import sys
from flask import Flask

# 新しいBlueprint（ルーティング定義）をインポート
from routes.auth_routes import auth_bp
from routes.receipt_routes import receipt_bp

app = Flask(__name__)

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
