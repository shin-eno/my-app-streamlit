from app import app, get_db_connection
import bcrypt
import os

def create_initial_admin():
    # Flaskのコンテキスト内で実行（必要に応じて）
    with app.app_context():
        user_id = "admin"
        user_name = "システム管理者"
        mail = "admin@example.com"
        password = "password123"  # ログイン後、画面から削除・変更してください

        # パスワードのハッシュ化（app.pyと同じロジック）
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # すでに存在するか確認
            cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if cur.fetchone():
                print(f"ユーザー '{user_id}' は既に存在します。")
                return

            # 管理者フラグを TRUE にして登録
            cur.execute(
                """
                INSERT INTO users (user_id, user_name, mail_address, password_hash, administrator_flg)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, user_name, mail, hashed_pw, True)
            )
            conn.commit()
            print(f"管理者ユーザー '{user_id}' を登録しました！")
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")
        finally:
            if cur: cur.close()
            if conn: conn.close()

if __name__ == "__main__":
    create_initial_admin()
