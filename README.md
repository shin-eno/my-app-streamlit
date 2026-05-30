"# my-app-streamlit" 
# initial git

git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/shin-eno/my-app-streamlit.git
git push -u origin main
info: please complete authentication in your browser...


# 初期構築時のセットアップ
docker exec -it my-app-backend python setup_admin.py

# webアクセスURL
アクセスURL：http://localhost:8501/

# 検証用メール
アクセスURL：http://localhost:8025

---

google driveの認証関連

[本システム (Flask)] + [token.json] ──(自動認証・期限自動更新)──> [Google Drive API]


---

## 2. 事前準備：Google Cloud 側での設定

まずは Google Cloud コンソール（新：Google Auth Platform）にて、適切な認証情報を作成します。

### Step 2-1: 外部ユーザー（テスト中）への変更とテストユーザーの登録
1. [Google Cloud コンソール](https://console.cloud.google.com/) にログインします。
2. 左上のメニューから **「API とサービス」 > 「OAuth 同意画面」**（または **「ブランディング」「対象（Audience）」**）を開きます。
3. アプリの公開ステータス（ユーザータイプ）を **「外部（External）」** または **「テスト中（Testing）」** に設定します。
4. **【重要】** **「対象（Audience）」** または **「テストユーザー（Test users）」** の項目にある **「+ ユーザーを追加（ADD USERS）」** をクリックします。
5. 運用（アップロード先）で利用するご自身の **Gmail アドレス** を入力して追加し、保存します。
   * ※ これを行わないと、認証時に `エラー 403: org_internal` や `access_denied` が発生します。

### Step 2-2: デスクトップアプリ用 credentials.json の発行
1. 「API とサービス」の **「認証情報（Credentials）」** 画面を開きます。
2. 画面上部の **「+ 認証情報を作成」** をクリックし、**「OAuth クライアント ID」** を選択します。
3. アプリケーションの種類として **「デスクトップ アプリ（Desktop app）」** を選択します。
4. 任意の名前（例: `Receipt-Uploader-Batch`）を入力し、**「作成」** をクリックします。
5. 完了画面、または一覧の右側にある **「JSON をダウンロード」** アイコンをクリックしてファイルを保存します。
6. ダウンロードしたファイルの名前を **`credentials.json`** に変更します。

---

## 3. 手順 A：開発環境（ローカル）での token.json 生成

本番環境のサーバー上では通常ブラウザが起動できないため、**「まず開発環境（手元のPC）で `token.json` を作り、それを本番環境へコピーする」** 流れが最もスムーズです。

### 📋 配置構成
`backend/` ディレクトリの中に `credentials.json` を配置します。
backend/
├── credentials.json  (Step 2-2 で取得したもの)
└── generate_token.py (トークン自動生成スクリプト)


### 💻 実行用スクリプト (`generate_token.py`)
```python
# backend/generate_token.py
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['[https://www.googleapis.com/auth/drive](https://www.googleapis.com/auth/drive)']

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', 
        scopes=SCOPES
    )
    
    try:
        # 自動でローカルサーバーを起動し、ブラウザで認証を通す
        creds = flow.run_local_server(
            host='localhost',
            port=0,
            prompt='select_account',
            success_message='🎉 認証に成功しました！このタブを閉じてスクリプトを確認してください。'
        )
    except Exception:
        # 環境によりブラウザ自動起動が失敗した場合はコンソールでのコピペ方式へ切り替え
        print("\\n--- 自動取得に失敗したため、手動認証を開始します ---")
        auth_url, _ = flow.authorization_url(prompt='select_account')
        print(f'\\n1. 以下のURLをブラウザで開いてログインしてください:\\n{auth_url}\\n')
        code = input('2. ログイン後に表示された「認証コード」を入力してください: ').strip()
        flow.fetch_token(code=code)
        creds = flow.credentials
    
    # token.json として保存
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("\\n🎉 token.json の生成に成功しました！")

if __name__ == '__main__':
    main()
⚙️ 実行手順
手元の PC のターミナル（WSL2 / コマンドプロンプト等）で backend/ へ移動します。

スクリプトを実行します。

Bash
python generate_token.py
ブラウザが自動起動し、Google のログイン画面が開きます。Step 2-1 でテストユーザーに登録した Gmail アカウント を選択します。

「このアプリは Google により検証されていません」という警告画面が出た場合は、「詳細」 > 「〜〜（安全ではないページ）に移動」 をクリックします。

アクセス権限の確認画面で 「続行（または許可）」 をクリックします。

ターミナルに 🎉 token.json の生成に成功しました！ と出力され、backend/token.json が生成されます。

4. 手順 B：本番環境へのデプロイと運用
本番環境（VPS / AWS / クラウド等）にシステムをデプロイする際の手順です。

Step 4-1: 成果物のコピー
開発環境で生成した credentials.json と token.json の 2 つを、本番環境サーバーの backend/ ディレクトリ配下にセキュアに（SCP や Git-Secret 等で）配置・コピーします。

Step 4-2: docker-compose.yml の設定
本番環境の Docker コンテナ内からもこれらの認証ファイルを永続的に参照できるように、volumes（マウント設定）を記述します。

YAML
  backend:
    build: ./backend
    container_name: my-app-backend
    volumes:
      - ./backend:/app
      - ./backend/credentials.json:/app/credentials.json
      - ./backend/token.json:/app/token.json  # ★ここが重要
    environment:
      - DB_HOST=db
      # ... その他の環境変数
Step 4-3: コンテナの起動・再ビルド
本番環境で以下のコマンドを実行し、コンテナをバックグラウンド起動します。

Bash
docker compose up -d --build
5. 有効期限とメンテナンスについて
🔄 トークンの自動更新（永続化）
本システムに組み込まれたバックエンドコードには、以下の機構が実装されています。

token.json 内部に保存された「アクセストークン」の有効期限（通常1時間）が切れると、内部の「リフレッシュトークン」を用いて、バックエンドが自動かつ裏側で Google 認証サーバーと通信し、トークンを最新の状態に更新（上書き保存）します。

そのため、一度本番環境へ配置した後は、原則として半永久的に人間の再ログイン操作なしで稼働し続けます。

⚠ 再認証が必要になるケース（例外）
以下の場合、リフレッシュトークンが無効化されるため、再度「手順 A」から token.json を再生成して本番へ配置し直す必要があります。

Google Cloud コンソール側で、OAuth クライアントの「クライアント シークレット」を変更・削除した場合。

Google アカウントのパスワードを変更した場合。

アプリの公開ステータスが「テスト中」のままで、7日間以上システムのアップロード処理が1度も実行されなかった場合（※テスト中ステータスのリフレッシュトークンは7日間の不活動で失効する仕様です）。

対策: 完全に永続化したい場合は、Google Cloud 側で同意画面のステータスを「検証（公開）」へ進めるか、定期的なバッチ稼働を維持してください。
"""

file_path = "Google_Drive_Auth_Manual.md"
with open(file_path, "w", encoding="utf-8") as f:
f.write(markdown_content.strip())

print(f"File generated successfully: {file_path}")

Your Markdown file is ready
[file-tag: code-generated-file-0-1779024148299370314]

無事に `token.json` の生成に成功したとのこと、本当におめでとうございます！数々の厳しいセキュリティブロックを乗り越えられて、素晴らしいエンジニアリングスキルです。

ご認識の通り、**本番環境でも全く同じ `token.json` と `credentials.json` のセットが必要**になります。ただし、本番サーバー上では通常ブラウザを開くことができないため、**「手元の開発環境で作った `token.json` を本番環境へコピー（デプロイ）する」** というのが、実務において最も手軽でスマートな王道の運用方法になります。

このあたりの「なぜこの作業が必要なのか」という理由から、開発環境での手順、本番環境への配置手順、そして運用後の有効期限（メンテナンス）に関する注意点までを体系的にまとめたマークダウン形式のマニュアル（`Google_Drive_Auth_Manual.md`）を作成しました。

今後の本番構築や、運用中に万が一トークンが切れた際の備忘録・仕様書としてぜひご活用ください。

---

### 📄 作成したマニュアルの構成概要

出力したマークdownファイルには、以下の内容が網羅されています。

1. **認証方式の概要**: なしてこの「リフレッシュトークン方式」が必要になったかの背景
2. **事前準備（Google Cloud側）**: 新画面（Google Auth Platform）における外部ユーザー・テストユーザー設定のまとめ
3. **手順A（開発環境での生成）**: ポート番号問題を完全に回避し、今回成功したデスクトップアプリ形式によるトークン生成スクリプトと実行手順
4. **手順B（本番環境へのデプロイ）**: 生成したファイルを本番へどうやって移し、`docker-compose.yml` でどうマウントすべきかの指示
5. **有効期限とメンテナンス**: トークンの自動更新の仕組みと、どういう時に再認証（再発行）が必要になるかの注意点

### 💡 本番運用に向けたワンポイントアドバイス
マニュアルの第5章にも記載していますが、今回作成した OAuth のステータスが「テスト中（Testing）」の場合、**「7日間一度もAPI（アップロード処理）が使われないと、セキュリティ制限によりリフレッシュトークンが自動失効する」** というGoogle側の仕様があります。

* **対策**: 週に1回以上レシートを登録するか、あるいは将来的にシステムを完全に放置しても動くようにしたい場合は、Google Cloudの「Google Auth Platform」画面からアプリの公開ステータスを「本番（検証・公開）」に進めることで、この7日間の期限制限を解除することができます。

まずは手元のDocker環境で、Streamlitから画像をアップロードした際に、エラーなくGoogle Driveへ保存され、D



---
### バッチとしてAPIを実行する場合
curl -X POST http://localhost:5000/api/receipts/batch-run

# powershellで実行する場合
Invoke-RestMethod -Uri "http://localhost:5000/api/receipts/batch-run" -Method Post
