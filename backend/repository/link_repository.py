import logging
import psycopg2
from psycopg2.extras import DictCursor
import os

logger = logging.getLogger(__name__)

class LinkRepository:
    @staticmethod
    def _get_connection():
        return psycopg2.connect(os.environ['DATABASE_URL'])

    @staticmethod
    def get_all_active_links():
        """論理削除（delete_flg = FALSE）されていないリンクを表示順に取得"""
        query = """
            SELECT id, site_name, url, category, display_order, description 
            FROM site_link_collect 
            WHERE delete_flg = FALSE
            ORDER BY display_order ASC, id DESC;
        """
        conn = LinkRepository._get_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_link(site_name, url, category, display_order, description):
        query = """
            INSERT INTO site_link_collect (site_name, url, category, display_order, description)
            VALUES (%s, %s, %s, %s, %s);
        """
        conn = LinkRepository._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (site_name, url, category, display_order, description))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_link(link_id, site_name, url, category, display_order, description):
        query = """
            UPDATE site_link_collect 
            SET site_name = %s, url = %s, category = %s, display_order = %s, description = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        conn = LinkRepository._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (site_name, url, category, display_order, description, link_id))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def soft_delete_link(link_id):
        """論理削除（delete_flgをTRUEにする）"""
        query = """
            UPDATE site_link_collect 
            SET delete_flg = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        conn = LinkRepository._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (link_id,))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()