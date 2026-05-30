import psycopg2
from psycopg2.extras import RealDictCursor
from utils.db_utils import get_db_connection

class UserRepository:
    """ユーザー情報、認証、権限マスタ、パスワードリセットなど『User』に閉じたDB操作を担うクラス"""

    @classmethod
    def find_user_by_id(cls, user_id):
        """有効なユーザーをIDで1件検索します"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT * FROM users WHERE user_id = %s AND delete_flg = FALSE", (user_id,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_menu_permissions(cls, is_admin):
        """ユーザーの管理者フラグに基づき、アクセス許可されたメニュー一覧を取得します"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = "SELECT page_title, file_path, icon, section_name FROM menu_permissions WHERE deleted_at IS NULL"
            if not is_admin:
                query += " AND is_admin_only = FALSE "
            query += " ORDER BY display_order ASC"
            cur.execute(query)
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    @classmethod
    def register_user(cls, user_id, user_name, mail_address, hashed_password):
        """新しいユーザーアカウントをDBに書き込みます"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO users (user_id, user_name, mail_address, password_hash)
                VALUES (%s, %s, %s, %s)
            """, (user_id, user_name, mail_address, hashed_password))
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def update_user_password(cls, user_id, new_password_hash):
        """指定されたユーザーのパスワードハッシュを上書き更新します"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", (new_password_hash, user_id))
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_all_active_users(cls):
        """管理画面用に、削除されていないアクティブなユーザー一覧を返却します"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT user_id, user_name, administrator_flg, created_at FROM users WHERE delete_flg = FALSE ORDER BY created_at DESC")
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    @classmethod
    def logical_delete_user(cls, user_id):
        """ユーザーを削除フラグ立て（論理削除）します。存在しない場合は False を返します"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if not cur.fetchone():
                return False
            cur.execute("UPDATE users SET delete_flg = TRUE, deleted_at = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def save_password_reset_token(cls, user_id, token, expires_at):
        """パスワード再設定用トークンを保存（すでにあれば上書き更新）します"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET token = EXCLUDED.token, expires_at = EXCLUDED.expires_at
            """, (user_id, token, expires_at))
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def find_reset_token(cls, token):
        """再設定トークンの情報をマッチング確認します"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT user_id, expires_at FROM password_resets WHERE token = %s", (token,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()

    @classmethod
    def delete_reset_token(cls, token):
        """使用済み・期限切れのトークンを物理削除して安全に処理を閉じます"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM password_resets WHERE token = %s", (token,))
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
