import os
import logging
from flask import Blueprint, request, jsonify

from repository.receipt_repository import ReceiptRepository
from services.google_drive_service import GoogleDriveService
from services.gemini_service import GeminiService
from utils.image_utils import generate_new_filename, resize_image

receipt_bp = Blueprint('receipt', __name__)
UPLOAD_FOLDER = os.environ['UPLOAD_FOLDER']

# このファイル専用のロガーを作成
logger = logging.getLogger(__name__)

@receipt_bp.route('/api/receipts/upload', methods=['POST'])
def upload_receipt():
    if 'file' not in request.files:
        return jsonify({"message": "ファイルが添付されていません"}), 400
        
    file = request.files['file']
    category_id = request.form.get('category_id')
    if not category_id:
        return jsonify({"message": "カテゴリIDが指定されていません"}), 400

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    temp_file_path = None
    try:
        new_filename = generate_new_filename(file.filename)
        temp_file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(temp_file_path)
        
        try:
            resize_image(temp_file_path, max_size=2000)
        except Exception as e:
            print(f"Resize warning: {e}")

        drive_service = GoogleDriveService()
        google_drive_file_id = drive_service.upload_file(temp_file_path, new_filename)
        
        ReceiptRepository.insert_uploaded_receipt(category_id, google_drive_file_id)
        return jsonify({"status": "success", "drive_file_id": google_drive_file_id, "message": "Google Driveへの保存とDB登録が完了しました"}), 200

    except Exception as e:
        return jsonify({"message": f"システムエラー: {str(e)}"}), 500

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@receipt_bp.route('/api/receipts/batch-run', methods=['POST'])
def run_batch():
    logger.info("レシート解析バッチ処理を開始します。")
    processed_count = 0
    errors_count = 0

    try:
        unprocessed_receipts = ReceiptRepository.get_unprocessed_receipts(limit=10)
        logger.debug(f"未処理のレシートを {len(unprocessed_receipts)} 件検知しました。")

        if not unprocessed_receipts:
            logger.info("未処理のレシートがないため、バッチを正常終了します。")
            
            return jsonify({"status": "success", "message": "未処理のレシートはありませんでした。"}), 200

        drive_service = GoogleDriveService()
        gemini_service = GeminiService()

        for receipt in unprocessed_receipts:
            db_id = receipt['id']
            file_id = receipt['google_drive_file_id']
            logger.debug(f"【処理中】DB_ID: {db_id}, Drive_File_ID: {file_id} の解析を開始。")
            
            try:
                image_bytes = drive_service.download_file_bytes(file_id)
                logger.debug(f"DB_ID: {db_id} の画像をGoogle Driveからダウンロード成功。")

                extracted_data = gemini_service.analyze_receipt(image_bytes)
                logger.debug(f"DB_ID: {db_id} のGemini解析が完了しました。データ: {extracted_data}")

                ReceiptRepository.update_receipt_success(db_id, extracted_data)
                logger.info(f"【成功】DB_ID: {db_id} のレシート解析・DB更新が完了しました。")
                processed_count += 1

            except Exception as item_error:
                logger.error(
                    f"【失敗】DB_ID: {db_id} の処理中にエラーが発生しました。理由: {str(item_error)}", 
                    exc_info=True  # これをつけると、エラーが起きた行番や詳細な理由が自動で全量ログに出ます！
                )

                ReceiptRepository.update_receipt_failed(db_id)
                errors_count += 1
                continue

        logger.info(f"バッチ処理が終了しました。成功: {processed_count}件, 失敗: {errors_count}件")
        
        return jsonify({"status": "success", "message": f"バッチ処理が完了しました。成功: {processed_count}件, 失敗: {errors_count}件"}), 200

    except Exception as e:
        logger.critical("バッチ処理全体に影響する致命的なエラーが発生しました。", exc_info=True)
        
        return jsonify({"message": f"バッチ全体エラー: {str(e)}"}), 500

@receipt_bp.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        categories = ReceiptRepository.get_all_categories()
        return jsonify(categories), 200
    except Exception as e:
        return jsonify({"message": f"カテゴリ取得エラー: {str(e)}"}), 500
