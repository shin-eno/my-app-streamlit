import os
import psycopg2

def get_db_connection():
    """
    データベースへの接続コネクションを確立して返却します。
    環境変数 DATABASE_URL がある場合はそちらを優先し、ない場合は個別の接続情報を参照します。
    """
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
        
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )
