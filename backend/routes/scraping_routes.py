import os
import logging
import threading
from flask import Blueprint, request, jsonify
from repository.scraping_repository import ScrapingRepository
from services.scraping_service import ScrapingService
from services.google_drive_service import GoogleDriveService

scraping_bp = Blueprint('scraping', __name__)
logger = logging.getLogger(__name__)

# 裏側（バックグラウンド）で実行する重い処理の実体
def bg_scraping_task(log_id, url, download_name):
    zip_file_path = None
    try:
        logger.info(f"[BG-Task] ID: {log_id} のバックグラウンド処理を開始しました。")
        
        service = ScrapingService()
        zip_file_path = service.execute_scraping_flow(url, download_name)
        
        # Google Driveへのアップロード
        drive_service = GoogleDriveService()
        scraping_folder_id = os.environ.get('SCRAPING_FOLDER_ID')
        if scraping_folder_id:
            drive_service.folder_id = scraping_folder_id
        
        drive_filename = f"{download_name}.zip"
        google_drive_file_id = drive_service.upload_file(zip_file_path, drive_filename)
        
        # 成功したらDBを SUCCESS に更新
        ScrapingRepository.update_status(log_id, 'SUCCESS')
        logger.info(f"[BG-Task] ID: {log_id} の処理が正常に完了しました。")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[BG-Task] ID: {log_id} の処理中にエラーが発生しました: {error_msg}", exc_info=True)
        # 失敗したらDBを FAILED に更新
        ScrapingRepository.update_status(log_id, 'FAILED', error_msg)
    finally:
        # 一時ファイルの消去
        if zip_file_path and os.path.exists(zip_file_path):
            try:
                os.remove(zip_file_path)
            except Exception as clean_error:
                logger.warning(f"[BG-Task] 一時ファイルの削除失敗: {clean_error}")

@scraping_bp.route('/api/scraping/run', methods=['POST'])
def run_scraping():
    data = request.json or {}
    url = data.get('url')
    download_name = data.get('download_name')

    if not url or not download_name:
        return jsonify({"message": "URLとファイル名は必須です"}), 400

    # 1. まずDBに「実行中(RUNNING)」として即座に登録
    log_id = ScrapingRepository.create_log(url, download_name)

    # 2. ★スレッドを立ち上げて、処理を裏側に丸投げする
    thread = threading.Thread(
        target=bg_scraping_task, 
        args=(log_id, url, download_name)
    )
    thread.start()  # 裏側で処理スタート（この関数自体は待たずに次へ進む）

    # 3. フロントには待たせることなく「受け付けました」と即答する (HTTP 202 Accepted)
    return jsonify({
        "status": "accepted",
        "message": "スクレイピング処理をバックグラウンドで開始しました。完了までしばらくお待ちください。",
        "log_id": log_id
    }), 202


@scraping_bp.route('/api/scraping/history', methods=['GET'])
def get_scraping_history():
    try:
        # リポジトリから過去10件のデータを取得
        history = ScrapingRepository.get_recent_logs(limit=10)
        return jsonify(history), 200
    except Exception as e:
        logger.error(f"履歴の取得に失敗しました: {e}", exc_info=True)
        return jsonify({"message": "履歴を取得できませんでした。"}), 500