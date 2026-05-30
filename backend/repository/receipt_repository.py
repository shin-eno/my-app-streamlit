import psycopg2
from psycopg2.extras import RealDictCursor
from utils.db_utils import get_db_connection

class ReceiptRepository:
    """レシート情報（receiptsテーブル）および品目カテゴリマスタに特化したDB操作を管理するクラス"""

    @classmethod
    def insert_uploaded_receipt(cls, category_id, google_drive_file_id):
        """アップロード直後のレシートレコードを下書き状態（10010）で新規登録します"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO receipts (category_id, google_drive_file_id, batch_status, created_at)
                VALUES (%s, %s, '10010', CURRENT_TIMESTAMP)
            """, (int(category_id), google_drive_file_id))
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_unprocessed_receipts(cls, limit=10):
        """バッチ自動解析用に、未処理（is_processed = False）のデータを古い順に最大N件引きます"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT id, google_drive_file_id FROM receipts WHERE is_processed = False ORDER BY created_at ASC LIMIT %s", (limit,))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    @classmethod
    def update_receipt_success(cls, db_id, extracted_data):
        """Geminiの解析結果（構造化データ）を反映し、処理完了（is_processed=True, 10090）にマークします"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE receipts 
                SET shop_name = %s, pay_date = %s, pay_time = %s, total_pay = %s,
                    is_processed = True, batch_status = '10090', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (extracted_data.get('shop_name'), extracted_data.get('pay_date'),
                  extracted_data.get('pay_time'), extracted_data.get('total_pay'), db_id))
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def update_receipt_failed(cls, db_id):
        """何らかのエラーでパースできなかったレコードに、スキップ用のエラーコード（99999）をマーキングします"""
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE receipts SET batch_status = '99999', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (db_id,))
            conn.commit()
        except:
            conn.rollback()
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_all_categories(cls):
        """画面のプルダウン項目生成用のカテゴリマスタを取得します"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT id, name FROM categories ORDER BY id ASC")
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()
