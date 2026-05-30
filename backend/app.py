from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import os
import io
import re

import json
from PIL import Image, ImageOps
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload

import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


app = Flask(__name__)

# -------------------------------------------------------------
# 環境変数の厳格なチェック（固定値は一切持たせない）
# -------------------------------------------------------------
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID')
if not DRIVE_FOLDER_ID:
    print("【CRITICAL ERROR】環境変数 'DRIVE_FOLDER_ID' が設定されていません。", file=sys.stderr)
    raise ValueError("Missing required environment variable: DRIVE_FOLDER_ID")

def get_db_connection():
    # DATABASE_URLがあればそれを使用し、なければ個別の環境変数（デフォルト値付き）で接続する
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)

    # Docker環境の変数を使用
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )



@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    u_id = data.get('user_id')
    password = data.get('password')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. ユーザーを検索（論理削除されていないもの）
        cur.execute("SELECT * FROM users WHERE user_id = %s AND delete_flg = FALSE", (u_id,))
        user = cur.fetchone()
        
        # 2. パスワード検証
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            is_admin = user['administrator_flg']
            
            # 3. 重要：menu_permissionsテーブルからアクセス可能なページリストを取得[cite: 3, 4]
            query = """
                SELECT
                    page_title,
                    file_path,
                    icon,
                    section_name 
                FROM
                    menu_permissions 
                WHERE
                    deleted_at IS NULL 
                    """
            # 管理者でない場合は、管理者専用ページを除外
            if not is_admin:
                query += " AND is_admin_only = FALSE "
            query += " ORDER BY display_order ASC"
            
            cur.execute(query)
            pages = cur.fetchall() # ここで pages を取得
            
            # 4. レスポンスを返却（'pages' キーを含める）[cite: 6]
            return jsonify({
                "message": "ログイン成功",
                "user": {
                    "user_id": user['user_id'],
                    "user_name": user['user_name'],
                    "is_admin": is_admin
                },
                "pages": pages  # ← これが不足していたためエラーが出ていました
            }), 200
        else:
            return jsonify({"message": "IDまたはパスワードが違います"}), 401
    except Exception as e:
        return jsonify({"message": f"サーバーエラー: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()


#
# ユーザ登録
#
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    mail = data.get('mail_address')
    password = data.get('password')

    # パスワードをハッシュ化（生パスワードは絶対にDBに入れない）
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (
                            user_id, 
                            user_name, 
                            mail_address, 
                            password_hash
                            )
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, user_name, mail, hashed_pw)
        )
        conn.commit()
        return jsonify({"message": "ユーザー登録が完了しました"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/api/users/change-password', methods=['POST'])
def change_password():
    data = request.json
    u_id = data.get('user_id')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not all([u_id, current_password, new_password]):
        return jsonify({"message": "入力項目が不足しています"}), 400
        
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1. 現在のユーザー情報を取得
        cur.execute("SELECT password_hash FROM users WHERE user_id = %s AND delete_flg = FALSE", (u_id,))
        user = cur.fetchone()
        
        if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({"message": "現在のパスワードが正しくありません"}), 401
            
        # 2. 新しいパスワードをハッシュ化して更新
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("""
            UPDATE users 
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = %s
        """, (new_password_hash, u_id))
        
        conn.commit()
        return jsonify({"message": "パスワードを更新しました"}), 200
        
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"message": f"エラーが発生しました: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

#
# ユーザ一覧出力
#
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 削除されていないユーザーを全件取得[cite: 5]
        cur.execute("SELECT " \
        "               user_id, " \
        "               user_name, " \
        "               administrator_flg, " \
        "               created_at" \
        "           FROM " \
        "               users" \
        "           WHERE " \
        "               delete_flg = FALSE" \
        "           ORDER BY created_at DESC"
        )
        users = cur.fetchall()

        return jsonify(users), 200
    
    except Exception as e:
        return jsonify({"message": f"ユーザー取得エラー: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()


#
# ユーザー削除
#
@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user_v2(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 1. ユーザーの存在確認
        cur.execute("SELECT" \
        "               user_id" \
        "            FROM" \
        "               users" \
        "           WHERE" \
        "               user_id = %s", (user_id,)
                    )

        if not cur.fetchone():
            return jsonify({"status": "error", "message": "ユーザーが見つかりません"}), 404

        # 2. 論理削除（delete_flgとdeleted_atの両方を更新）
        cur.execute("""
            UPDATE
                users 
            SET
                delete_flg = TRUE, 
                deleted_at = CURRENT_TIMESTAMP 
            WHERE
                user_id = %s
            """, (user_id,))

        conn.commit()
        return jsonify({
            "status": "success", 
            "message": f"ユーザー {user_id} を削除しました"
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# トークン発行とメール送信API
@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    u_id = data.get('user_id')
    
    # 本来はここでユーザーのメールアドレスをDBから取得します
    # 今回は構成上、簡易的に処理します
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(minutes=30)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # トークンを保存（既存のトークンがあれば上書き）
        cur.execute("""
            INSERT INTO password_resets (user_id, token, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET token = EXCLUDED.token, expires_at = EXCLUDED.expires_at
        """, (u_id, token, expires_at))
        conn.commit()
        
        # メール送信（設定は環境に合わせて調整してください）
        # ※ 実際にはフロントエンドのURL（http://localhost:8501/reset_password?token=...）を送ります
        send_reset_email("user@example.com", token)
        
        return jsonify({"message": "再設定メールを送信しました"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

#
# リセットメール送信
#
def send_reset_email(to_email, token):
    # 送信元・先の設定
    smtp_server = "mailpit" # コンテナ名
    smtp_port = 1025
    sender_email = "system@example.com"
    
    # リセットURLの構築（FrontendのURL）
    reset_url = f"http://localhost:8501/?token={token}"
    
    # メールの作成
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = "【重要】パスワード再設定のご案内"
    
    body = f"""
    パスワード再設定のリクエストを受け付けました。
    以下のリンクをクリックして、30分以内に新しいパスワードを設定してください。

    {reset_url}

    ※心当たりがない場合は、このメールを破棄してください。
    """
    message.attach(MIMEText(body, "plain"))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.sendmail(sender_email, to_email, message.as_string())
        print(f"Mail sent to {to_email} via Mailpit")
    except Exception as e:
        print(f"Mail error: {e}")


#
# パスワードリセット処理
#
@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({"message": "必要な情報が不足しています"}), 400
        
    conn = get_db_connection()
    cur = conn.cursor() # ※もしDictCursor等を使っている場合は、以下を適宜調整してください
    try:
        # 1. トークンが password_resets テーブルに存在するか確認
        cur.execute("""
            SELECT user_id, expires_at 
            FROM password_resets 
            WHERE token = %s
        """, (token,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({"message": "トークンが無効であるか、既に使われています"}), 400
            
        # タプルのインデックス、または辞書のキーで取得
        user_id = row[0] if isinstance(row, tuple) else row['user_id']
        expires_at = row[1] if isinstance(row, tuple) else row['expires_at']
        
        # 2. 有効期限のチェック（現在時刻を過ぎていたらNG）
        if expires_at < datetime.now():
            cur.execute("DELETE FROM password_resets WHERE token = %s", (token,))
            conn.commit()
            return jsonify({"message": "トークンの有効期限（30分）が切れています"}), 400

        # 3. 新しいパスワードをハッシュ化して users テーブルを更新
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("""
            UPDATE users 
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = %s
        """, (new_password_hash, user_id))
        
        # 4. セキュリティのため、使用済みのトークンをテーブルから削除
        cur.execute("DELETE FROM password_resets WHERE token = %s", (token,))
        
        conn.commit()
        return jsonify({"message": "パスワードを正常に更新しました"}), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"message": f"サーバーエラーが発生しました: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()


#
# レシート解析 & Google Drive保存API
#

def resize_image_bytes(image_bytes, max_size=2000):
    """画像を長辺max_size以下にリサイズしてバイトデータを返すヘルパー関数"""
    img = Image.open(io.BytesIO(image_bytes))
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except:
        pass
    
    width, height = img.size
    if max(width, height) > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    return output.getvalue()



# 一時ファイルを保存するディレクトリ
UPLOAD_FOLDER = '/tmp/receipt_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# １．新しいファイル名を生成するヘルパー関数
def generate_new_filename(original_filename):
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = os.path.splitext(original_filename)[1] # 拡張子 (.jpg など) を取得
    return f"receipt_{now}{ext}"

# ３．ファイルをリサイズする関数
def resize_image(file_path, max_size=2000):
    with Image.open(file_path) as img:
        # EXIF情報（スマホ撮影の向き）を維持
        try:
            img = ImageOps.exif_transpose(img)
        except:
            pass

        width, height = img.size
        if max(width, height) > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # JPEG形式で上書き保存
        img.save(file_path, format="JPEG", quality=85)


@app.route('/api/receipts/upload', methods=['POST'])
def upload_receipt():
    if 'file' not in request.files:
        return jsonify({"message": "ファイルが添付されていません"}), 400
        
    file = request.files['file']
    category_id = request.form.get('category_id')
    
    if not category_id:
        return jsonify({"message": "カテゴリIDが指定されていません"}), 400

    # ★最初に関数を None で初期化しておくことで、UnboundLocalError を防ぎます
    conn = None
    cur = None
    temp_file_path = None

    try:
        # １．新しいファイル名を生成する
        new_filename = generate_new_filename(file.filename)
        temp_file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        
        # ２．ファイルを一時的にOSに保存する
        file.save(temp_file_path)
        
        # ３．googleDriveへアップロードする前に、ファイルをリサイズする
        try:
            resize_image(temp_file_path, max_size=2000)
        except Exception as e:
            print(f"Resize warning: {e}")

        # ４．OAuth 2.0 クライアント認証（token.json ）を使用してGoogle Driveへ
        # アップロードし、アップロード後のdriveIdを取得する
        drive_file_id = None
        token_path = os.environ.get('GOOGLE_TOKEN_PATH', '/app/token.json')
        
        if os.path.exists(token_path):
            SCOPES = ['https://www.googleapis.com/auth/drive']
            # token.json (リフレッシュトークン入り) を使って認証
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # トークンの有効期限が切れていた場合は、credentials.jsonを使って自動で更新（リフレッシュ）
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                # 更新された新しいトークンを保存
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            drive_service = build('drive', 'v3', credentials=creds)
            
            file_metadata = {
                'name': new_filename,
                'parents': [DRIVE_FOLDER_ID]
            }
            media = MediaFileUpload(temp_file_path, mimetype='image/jpeg', resumable=True)
            drive_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            google_drive_file_id = drive_file.get('id')
        else:
            return jsonify({"message": "Google Driveの認証トークン(token.json)が見つかりません。事前に生成してください。"}), 500
        # ５．DBに登録する
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO receipts (category_id, google_drive_file_id, batch_status, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (int(category_id), google_drive_file_id,"10010"))
        
        conn.commit()
        
        # 処理が終わったら一時ファイルを削除
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return jsonify({
            "status": "success", 
            "drive_file_id": drive_file_id,
            "message": "Google Driveへの保存とDB登録が完了しました"
        }), 200

    except Exception as e:
        # ★安全なエラーハンドリングに変更（変数存在チェックを入れる）
        if conn is not None: 
            conn.rollback()
        if temp_file_path is not None and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        # 本物のエラー原因（MalformedErrorなど）をフロントに綺麗に返します
        return jsonify({"message": f"システムエラー: {str(e)}"}), 500
    finally:
        if cur is not None: cur.close()
        if conn is not None: conn.close()

# -------------------------------------------------------------
# ② バッチ実行用エンドポイント（外部APIやStreamlitから叩いて一括処理）
# -------------------------------------------------------------
@app.route('/api/receipts/batch-run', methods=['POST'])
def run_batch():
    conn = None
    cur = None
    processed_count = 0
    errors_count = 0

    try:
        # 1. DBから未処理(is_processed = False)のレシートを最大10件取得
        conn = get_db_connection()
        # RealDictCursorを使ってカラム名で扱いやすくします
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT id, google_drive_file_id 
            FROM receipts 
            WHERE is_processed = False 
            ORDER BY created_at ASC 
            LIMIT 10
        """)
        unprocessed_receipts = cur.fetchall()

        if not unprocessed_receipts:
            return jsonify({"status": "success", "message": "未処理のレシートはありませんでした。"}), 200

        # 2. Google Drive サービスと Gemini クライアントの初期化
        # (コンテナ内の環境変数 GEMINI_API_KEY を自動取得)
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        client = genai.Client(api_key=gemini_api_key)
        
        # Drive認証 環境変数から取得
        credentials_path = os.environ('GOOGLE_CREDENTIALS_PATH')
        token_path = os.environ('GOOGLE_TOKEN_PATH')


        if os.path.exists(token_path):
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive'])
        else:
            creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)

        # 3. 未処理レコードをループ処理 (batch.pyのコアロジック)
        for receipt in unprocessed_receipts:
            db_id = receipt['id']
            file_id = receipt['google_drive_file_id']
            
            try:
                # Driveから画像をダウンロード (メモリ上のバイナリストリームに展開)
                from googleapiclient.http import MediaIoBaseDownload
                import io
                
                request_file = drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request_file)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                # Gemini 2.0 APIによる解析（batch.pyで動作実績のある記述に準拠）
                # ※モデル名：'gemini-2.0-flash-lite' または 'models/gemini-flash-latest'
                response = client.models.generate_content(
                    model='models/gemini-flash-latest',
                    contents=[
                        "添付したレシートの写真から店名、日付(YYYY-MM-DD)、時間(HH:mm)、合計金額を抽出してJSON形式でのみ答えてください。キー名は shop_name, pay_date, pay_time, total_pay としてください。",
                        types.Part.from_bytes(data=fh.getvalue(), mime_type="image/jpeg")
                    ]
                )

                # レスポンスのクレンジング
                clean_json = re.sub(r'^```json\s*|\s*```$', '', response.text.strip(), flags=re.MULTILINE)
                extracted_data = json.loads(clean_json)

                # 解析結果でDBを更新
                update_sql = """
                    UPDATE receipts 
                    SET shop_name = %s, 
                        pay_date = %s, 
                        pay_time = %s, 
                        total_pay = %s,
                        is_processed = True,
                        batch_status = '10090',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cur.execute(update_sql, (
                    extracted_data.get('shop_name'),
                    extracted_data.get('pay_date'),
                    extracted_data.get('pay_time'),
                    extracted_data.get('total_pay'),
                    db_id
                ))
                conn.commit()
                processed_count += 1

            except Exception as item_error:
                print(f"ID:{db_id} の処理中にエラーが発生しました: {str(item_error)}")
                if conn is not None:
                    conn.rollback()
                errors_count += 1
                # 失敗した場合はステータスを更新して、無限ループを防ぐ（リトライ対象外にする、あるいはログを残す）
                try:
                    cur.execute("""
                        UPDATE receipts 
                        SET batch_status = '99999', updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (db_id,))
                    conn.commit()
                except:
                    pass
                continue

        return jsonify({
            "status": "success",
            "message": f"バッチ処理が完了しました。成功: {processed_count}件, 失敗: {errors_count}件"
        }), 200

    except Exception as e:
        return jsonify({"message": f"バッチ全体エラー: {str(e)}"}), 500
    finally:
        if cur is not None: cur.close()
        if conn is not None: conn.close()

#
#　カテゴリ情報取得
#
@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    # 既存のRealDictCursorを使用して、キー名で取得できるようにします
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # DBからIDとカテゴリ名を取得
        cur.execute("SELECT id, name FROM categories ORDER BY id ASC")
        categories = cur.fetchall()
        return jsonify(categories), 200
    except Exception as e:
        return jsonify({"message": f"カテゴリ取得エラー: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

#
# flask実行
#
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

