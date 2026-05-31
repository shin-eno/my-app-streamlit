import logging
import psycopg2
from psycopg2.extras import DictCursor
import os

logger = logging.getLogger(__name__)

class ScrapingRepository:
    @staticmethod
    def _get_connection():
        return psycopg2.connect(os.environ['DATABASE_URL'])

    @staticmethod
    def create_log(url, download_name):
        """初期実行レコードを登録し、発行されたIDを返す"""
        query = """
            INSERT INTO scraping_logs (target_url, download_name, status)
            VALUES (%s, %s, 'RUNNING') RETURNING id;
        """
        conn = ScrapingRepository._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (url, download_name))
                log_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[DB] スクレイピングログを登録しました。ID: {log_id}")
                return log_id
        except Exception as e:
            conn.rollback()
            logger.error(f"ログ登録に失敗しました: {e}", exc_info=True)
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_status(log_id, status, error_message=None):
        """ステータスを更新する（SUCCESS または FAILED）"""
        query = """
            UPDATE scraping_logs
            SET status = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        conn = ScrapingRepository._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (status, error_message, log_id))
                conn.commit()
                logger.info(f"[DB] ID: {log_id} のステータスを {status} に更新しました。")
        except Exception as e:
            conn.rollback()
            logger.error(f"ステータス更新に失敗しました: {e}", exc_info=True)
        finally:
            conn.close()
