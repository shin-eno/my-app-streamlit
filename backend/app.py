from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import os

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


#
# flask実行
#
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

