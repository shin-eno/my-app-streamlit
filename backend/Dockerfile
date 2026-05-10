# ベースイメージの指定
FROM python:3.13-slim

# コンテナ内の環境変数を設定（Pythonがバッファリングをせずに出力するようにする）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 作業ディレクトリの設定
WORKDIR /app

# 依存関係のインストールに必要な最小限のパッケージをインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtを先にコピー（キャッシュを効率的に使うため）
COPY requirements.txt .

# 依存ライブラリのインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションソースコードのコピー
COPY . .

# Flaskのポート開放
EXPOSE 5000

# Flaskの開発用サーバーを起動
# ホストを 0.0.0.0 にすることでコンテナ外からの通信を許可します
CMD ["python", "app.py"]
