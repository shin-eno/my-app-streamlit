import os
import logging
from flask import Blueprint, request, jsonify
from repository.scraping_repository import ScrapingRepository
from services.scraping_service import ScrapingService
# ↓ GoogleDriveService をインポートします
from services.google_drive_service import GoogleDriveService

scraping_bp = Blueprint('scraping', __name__)
logger = logging.getLogger(__name__)

@scraping_bp.route('/api/scraping/run', methods=['POST'])
def run_scraping():
    data = request.json or {}
    url = data.get('url')
    download_name = data.get('download_name')

    if not url or not download_name:
        return jsonify({"message": "URLとファイル名は必須です"}), 400

    # 1. DBに実行中ステータスでログを登録
    log_id = ScrapingRepository.create_log(url, download_name)

    # 最終的なローカルのZIPパスを保持する変数
    zip_file_path = None

    try:
        # 2. スクレイピング処理の実行（ローカル一時フォルダへのZIP化まで）
        service = ScrapingService()
        zip_file_path = service.execute_scraping_flow(url, download_name)
        
        # 3. 【パターン3追加】Google Drive へのアップロード処理
        logger.info(f"Google DriveへのZIPアップロードを開始します。対象: {zip_file_path}")
        
        drive_service = GoogleDriveService()
        
        # 今回提示された専用フォルダIDを一時的にセットしてアップロード
        scraping_folder_id = os.environ.get('SCRAPING_FOLDER_ID')
        if scraping_folder_id:
            drive_service.folder_id = scraping_folder_id
        
        # Drive上のファイル名（例: example_images.zip）
        drive_filename = f"{download_name}.zip"
        
        # アップロード実行 ➔ 完了するとDrive上の一意のIDが返ってきます
        google_drive_file_id = drive_service.upload_file(zip_file_path, drive_filename)
        logger.info(f"Google Driveへの転送が正常に完了しました。Drive_ID: {google_drive_file_id}")
        
        # 4. 正常終了したらDBを更新
        ScrapingRepository.update_status(log_id, 'SUCCESS')
        return jsonify({
            "status": "success", 
            "message": "スクレイピング、画像変換、ZIP圧縮、およびGoogle Driveへのアップロードがすべて正常に完了しました！",
            "drive_file_id": google_drive_file_id
        }), 200

    except Exception as e:
        # 5. 異常終了した場合もDBにエラー内容を書き込む
        error_msg = str(e)
        logger.error(f"スクレイピング・アップロード処理中にエラーが発生しました(ID: {log_id}): {error_msg}", exc_info=True)
        ScrapingRepository.update_status(log_id, 'FAILED', error_msg)
        return jsonify({"status": "failed", "message": f"処理中にエラーが発生しました: {error_msg}"}), 500

    finally:
        # 6. 【最重要】コンテナ内に残ったZIPファイルを確実に削除してディスクをクリーンに保つ
        if zip_file_path and os.path.exists(zip_file_path):
            try:
                os.remove(zip_file_path)
                logger.debug(f"コンテナ内の一時ZIPファイルを削除しました: {zip_file_path}")
            except Exception as clean_error:
                logger.warning(f"一時ZIPファイルの削除に失敗しました: {clean_error}")