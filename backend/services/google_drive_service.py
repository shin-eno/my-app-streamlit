import os
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

class GoogleDriveService:
    """Google Drive APIとの通信および認証を管理するサービス oily クラス"""

    def __init__(self):
        """環境変数から各種設定パスを読み込み、Google Drive サービスインスタンスを初期化します"""
        self.credentials_path = os.environ['GOOGLE_CREDENTIALS_PATH']
        self.token_path = os.environ['GOOGLE_TOKEN_PATH']

        self.folder_id = os.environ.get('DRIVE_FOLDER_ID')

        self.service = self._authenticate()

    def _authenticate(self):
        """
        OAuth2.0のトークンベース、またはサービスアカウントを用いてGoogle APIの認証を通します。
        
        Returns:
            googleapiclient.discovery.Resource: 認証済みのDriveサービスAPIクライアント
        """
        # 1. 優先：有効なローカル生成 token.json（OAuth2.0）があればそれを読み込む
        if os.path.exists(self.token_path):
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(self.token_path, ['https://www.googleapis.com/auth/drive'])
        # 2. 予備：token.jsonがない場合は、サービスアカウント（credentials.json）での認証を試行
        else:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
        # v3の仕様に合わせて API サービスをビルドして返却
        return build('drive', 'v3', credentials=creds)

    def download_file_bytes(self, file_id):
        """
        指定されたGoogle DriveのファイルIDから、画像バイナリをメモリ上に直接ダウンロードします。
        
        ※ローカルのOSディスクに一時ファイルを書き出さないため、ファイル削除漏れの心配がなく安全です。
        
        Args:
            file_id (str): Google Drive上のファイルID（google_drive_file_id）
        Returns:
            bytes: 画像ファイルの生バイナリデータ
        """
        # メディアストリームとしてのダウンロードリクエストを作成
        request_file = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()  # メモリ上のバッファストリームを用意
        downloader = MediaIoBaseDownload(fh, request_file)
        
        # チャンクごとに分割してダウンロードを実行（完了するまでループ）
        done = False
        while not done:
            _, done = downloader.next_chunk()
            
        return fh.getvalue()  # バッファに溜まったバイトデータを返却

    def upload_file(self, file_path, filename):
        """
        ローカルの一時ファイルを、指定されたGoogle Driveのフォルダへアップロードします。
        
        Args:
            file_path (str): ローカルファイルへの絶対パス（例: /tmp/receipt_uploads/xxx.jpg）
            filename (str): Google Drive上で保存するファイル名
        Returns:
            str: アップロード完了後に発行された Google Drive の一意のファイルID
        """
        # Google Drive上のファイル情報（メタデータ）を設定
        file_metadata = {
            'name': filename,
            'parents': [self.folder_id] if self.folder_id else []  # 保存先フォルダを指定
        }
        
        # アップロードするファイルのメディア設定（JPEGやPNGに対応できるよう、汎用的なストリーム形式を指定）
        media = MediaFileUpload(file_path, mimetype='application/octet-stream', resumable=True)
        
        # APIを実行してアップロード
        drive_file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        # 生成された一意のファイルIDを返却
        return drive_file.get('id')
