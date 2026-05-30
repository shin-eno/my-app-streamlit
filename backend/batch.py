import os
import json
import re
import psycopg2
import psycopg2.extras
from googleapiclient.discovery import build
from google.auth import default
from google import genai
from google.genai import types
import io
from googleapiclient.http import MediaIoBaseDownload

# --- 設定 ---
SOURCE_FOLDER_ID = '1rdEsglegc0xYjfe4CYwAC-Cr9d7U50ZE'  # 読み取り元
SOURCE_FOLDER_ID = '1obk9WiQP14WxI__4_eOC0d4Yn2ymoQMb'  # 読み取り元　検証

gemini_model= 'gemini-2.0-flash-lite'                   #
gemini_model= 'models/gemini-flash-latest'              # 無料で制限なし

LIMIT_COUNT = 10  # 1日の制限に合わせた上限

DB_CONFIG = {
    "dbname": "mydb",
    "user": "user",
    "password": "pass",
    "host": "127.0.0.1",
    "port": "5432"
}

def get_drive_service():
    scopes = ['https://www.googleapis.com/auth/drive']
    creds, _ = default(scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def run_batch_process():
    print("処理開始")

    # 1. DBから未処理のデータを最大10件取得
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT" \
    "               id, " \
    "               google_drive_file_id, " \
    "               category_id " \
    "             FROM" \
    "               receipts WHERE is_processed = False and " \
    "               batch_status='10010'" \
    "             LIMIT 10")

    targets = cur.fetchall()

    if not targets:
        print("未処理のデータはありません。")
        cur.close()
        conn.close()
        return

    service = get_drive_service()
    client = genai.Client(api_key="AIzaSyCTL5Np9Rkw8tuWz5DwN21BCyMBk6le5Eo")

#   print("利用可能なモデル一覧:")
#   for m in client.models.list():
#     print(f" - {m.name}")

    for row in targets:
        db_id = row['id']
        drive_file_id = row['google_drive_file_id']
        fh = None
        try:
            # 2. ファイルのダウンロード
            print(f"ID:{db_id} のファイルをダウンロード中...")
            request = service.files().get_media(fileId=drive_file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False

            while done is False:
                status, done = downloader.next_chunk()

            if fh.getvalue() == b"":
                raise Exception("ファイルのダウンロードに失敗しました（データが空です）")

            # 3. Geminiに連携
            print(f"ID:{db_id} をGeminiで解析中...")
            response = client.models.generate_content(
                model=gemini_model,
                contents=[
                    "添付したレシートの写真から店名、日付(YYYY-MM-DD)、時間(HH:mm)、合計金額を抽出してJSON形式でのみ答えてください。キー名は shop_name, pay_date, pay_time, total_pay としてください。",
                    types.Part.from_bytes(data=fh.getvalue(), mime_type="image/jpeg")
                ]
            )

            # 4. responseを取得した後にテキストをクレンジング (ここが正しい位置です)
            clean_json = re.sub(r'^```json\s*|\s*```$', '', response.text.strip(), flags=re.MULTILINE)
            extracted_data = json.loads(clean_json)

            # 5. 解析結果でDBを「更新」 ( .get() に修正)
            update_sql = '''
                UPDATE
                    receipts 
                SET
                    shop_name = %s, 
                    pay_date = %s, 
                    pay_time = %s, 
                    total_pay = %s,
                    is_processed = True,
                    batch_status = '10090',
                    updated_at = current_timestamp
                WHERE id = %s
            '''
            cur.execute(update_sql, (
                extracted_data.get('shop_name'),
                extracted_data.get('pay_date'),
                extracted_data.get('pay_time'),
                extracted_data.get('total_pay'),
                db_id
            ))

            conn.commit()
            print(f"ID:{db_id} の解析が完了しました。")

        except Exception as e:
            print(f"ID:{db_id} でエラー発生: {e}")
            conn.rollback()
        finally:
            if fh:
                fh.close()

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_batch_process()
