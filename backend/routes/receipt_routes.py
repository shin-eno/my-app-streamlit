import os
from flask import Blueprint, request, jsonify

from repository.receipt_repository import ReceiptRepository
from services.google_drive_service import GoogleDriveService
from services.gemini_service import GeminiService
from utils.image_utils import generate_new_filename, resize_image

receipt_bp = Blueprint('receipt', __name__)
UPLOAD_FOLDER = '/tmp/receipt_uploads'

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
    processed_count = 0
    errors_count = 0

    try:
        unprocessed_receipts = ReceiptRepository.get_unprocessed_receipts(limit=10)
        if not unprocessed_receipts:
            return jsonify({"status": "success", "message": "未処理のレシートはありませんでした。"}), 200

        drive_service = GoogleDriveService()
        gemini_service = GeminiService()

        for receipt in unprocessed_receipts:
            db_id = receipt['id']
            file_id = receipt['google_drive_file_id']
            try:
                image_bytes = drive_service.download_file_bytes(file_id)
                extracted_data = gemini_service.analyze_receipt(image_bytes)
                ReceiptRepository.update_receipt_success(db_id, extracted_data)
                processed_count += 1
            except Exception as item_error:
                print(f"ID:{db_id} の処理中にエラーが発生しました: {str(item_error)}")
                ReceiptRepository.update_receipt_failed(db_id)
                errors_count += 1
                continue

        return jsonify({"status": "success", "message": f"バッチ処理が完了しました。成功: {processed_count}件, 失敗: {errors_count}件"}), 200
    except Exception as e:
        return jsonify({"message": f"バッチ全体エラー: {str(e)}"}), 500

@receipt_bp.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        categories = ReceiptRepository.get_all_categories()
        return jsonify(categories), 200
    except Exception as e:
        return jsonify({"message": f"カテゴリ取得エラー: {str(e)}"}), 500
