# backend/generate_token.py
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    # 新しく作成した「デスクトップアプリ用」の credentials.json を読み込む
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', 
        scopes=SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob' # リダイレクトせず画面にコードを出す指定
    )
    
    # run_console() を使うことで、ポートを一切使わずにコンソール上で完結させます
    # (内部仕様でブラウザが立ち上がるか、もしくはURLがコンソールに出力されます)
    try:
        creds = flow.run_local_server(
            host='localhost',
            port=0, # ポート自動割り当てを任せますが、デスクトップアプリ用の認証ならミスマッチが起きません
            prompt='select_account',
            success_message='🎉 認証に成功しました！このタブを閉じてスクリプトを確認してください。'
        )
    except Exception:
        # 万が一ローカルサーバー方式が弾かれた場合のセーフティとして、完全コンソール入力方式を実行
        print("\n--- ローカルサーバーでの自動取得に失敗したため、手動認証を開始します ---")
        auth_url, _ = flow.authorization_url(prompt='select_account')
        print(f'\n1. 以下のURLをブラウザで開いてログインしてください:\n{auth_url}\n')
        code = input('2. ログイン完了後に画面に表示された「認証コード」をここに貼り付けてEnterを押してください: ').strip()
        flow.fetch_token(code=code)
        creds = flow.credentials
    
    # 認証結果を token.json として保存
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("\n🎉 token.json の生成に成功しました！")

if __name__ == '__main__':
    main()