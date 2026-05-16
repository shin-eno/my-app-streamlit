from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import os

import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

def get_db_connection():
    # Docker環境の変数を使用
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        database=os.environ.get('DB_NAME', 'mydb'),
        user=os.environ.get('DB_USER', 'user'),
        password=os.environ.get('DB_PASSWORD', 'pass')
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
# flask実行
#
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

