from flask import Flask, request, jsonify
from flask_cors import CORS
from psycopg2.extras import RealDictCursor

import psycopg2
import bcrypt

import os
import datetime
import time


app = Flask(__name__)
# Streamlitコンテナからのアクセスを許可するためにCORSを設定
CORS(app)

# 環境変数から接続情報を取得（設定がない場合のデフォルト値も指定）
#DATABASE_URL = os.environ.get('DATABASE_URL', "host=db port=5432 dbname=mydb user=user password=pass")
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 
    "postgresql://user:pass@db:5432/mydb"
)

#----- テスト用の接続ロジック開始 -----
def get_db_connection():
    """DBが起動するまでリトライしながら接続を試みる"""
    retries = 5
    while retries > 0:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except psycopg2.OperationalError as e:
            retries -= 1
            print(f"DB起動待ち... あと {retries} 回試行します: {e}")
            time.sleep(2)  # 2秒待機
    raise Exception("DBへの接続に失敗しました")


#
# システムのステータスと現在時刻を返す簡単なAPI
#
@app.route('/api/status', methods=['GET'])
def get_status():
    """
    システムのステータスと現在時刻を返す簡単なAPI
    """
    return jsonify({
        "status": "online",
        "message": "Flask Backend is running smoothly!",
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


#
# テスト用DB接続確認
#
@app.route('/api/db-check', methods=['GET'])
def db_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # 疎通確認のためのクエリ実行
        cur.execute('SELECT version();')

        db_version = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({
            "status": "connected",
            "database": "PostgreSQL",
            "version": db_version
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# --- DB接続関数 ---
def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

#----- テスト用の接続ロジック終了 -----

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
            INSERT INTO users (user_id, user_name, mail_address, password_hash)
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

#
# ユーザリスト出力
#
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        # RealDictCursorを使うと、結果を辞書形式（列名付き）で取得できて便利です
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, user_id, user_name, mail_address, administrator_flg, delete_flg, created_at 
            FROM users 
            WHERE delete_flg = FALSE
            ORDER BY id ASC
        """)
        
        users = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#
# ユーザ削除
#
@app.route('/api/users/<u_id>', methods=['DELETE'])
def delete_user(u_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # delete_flgをTRUEに更新
        cur.execute(
            "UPDATE users SET delete_flg = TRUE, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
            (u_id,)
        )
        conn.commit()
        
        if cur.rowcount == 0:
            return jsonify({"error": "ユーザーが見つかりません"}), 404
            
        cur.close()
        conn.close()
        return jsonify({"message": f"ユーザー {u_id} を削除しました"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#
# ログイン処理
#

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    u_id = data.get('user_id')
    password = data.get('password')

    if not u_id or not password:
        return jsonify({"error": "IDとパスワードを入力してください"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 有効なユーザー（delete_flg = FALSE）のみ取得
        cur.execute(
            "SELECT user_id, user_name, password_hash, administrator_flg FROM users WHERE user_id = %s AND delete_flg = FALSE",
            (u_id,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # パスワード一致！
            # 本来はここでJWTなどを返しますが、まずはシンプルにユーザー情報を返します
            return jsonify({
                "message": "ログイン成功",
                "user": {
                    "user_id": user['user_id'],
                    "user_name": user['user_name'],
                    "is_admin": user['administrator_flg']
                }
            }), 200
        else:
            return jsonify({"error": "ユーザーIDまたはパスワードが正しくありません"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    # Dockerコンテナ外（Streamlit側）から接続可能にするため 0.0.0.0 で起動
    #app.run(host='0.0.0.0', port=5000)

    # debug=True にすることでホットリロードが有効になります
    app.run(host='0.0.0.0', port=5000, debug=True)


