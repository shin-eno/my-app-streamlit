import bcrypt
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

from repository.user_repository import UserRepository
from utils.mail_utils import send_reset_email

# ルーターの定義
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    u_id = data.get('user_id')
    password = data.get('password')
    
    try:
        user = UserRepository.find_user_by_id(u_id)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            is_admin = user['administrator_flg']
            pages = UserRepository.get_menu_permissions(is_admin)
            return jsonify({
                "message": "ログイン成功",
                "user": {"user_id": user['user_id'], "user_name": user['user_name'], "is_admin": is_admin},
                "pages": pages
            }), 200
        return jsonify({"message": "IDまたはパスワードが違います"}), 401
    except Exception as e:
        return jsonify({"message": f"サーバーエラー: {str(e)}"}), 500

@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    mail = data.get('mail_address')
    password = data.get('password')

    try:
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        UserRepository.register_user(user_id, user_name, mail, hashed_pw)
        return jsonify({"message": "ユーザー登録が完了しました"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route('/api/users/change-password', methods=['POST'])
def change_password():
    data = request.json or {}
    u_id = data.get('user_id')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not all([u_id, current_password, new_password]):
        return jsonify({"message": "入力項目が不足しています"}), 400
        
    try:
        user = UserRepository.find_user_by_id(u_id)
        if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({"message": "現在のパスワードが正しくありません"}), 401
            
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        UserRepository.update_user_password(u_id, new_password_hash)
        return jsonify({"message": "パスワードを更新しました"}), 200
    except Exception as e:
        return jsonify({"message": f"エラーが発生しました: {str(e)}"}), 500

@auth_bp.route('/api/users', methods=['GET'])
def get_users():
    try:
        users = UserRepository.get_all_active_users()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"message": f"ユーザー取得エラー: {str(e)}"}), 500

@auth_bp.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        if not UserRepository.logical_delete_user(user_id):
            return jsonify({"status": "error", "message": "ユーザーが見つかりません"}), 404
        return jsonify({"status": "success", "message": f"ユーザー {user_id} を削除しました"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    u_id = data.get('user_id')
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(minutes=30)
    
    try:
        UserRepository.save_password_reset_token(u_id, token, expires_at)
        send_reset_email("user@example.com", token)
        return jsonify({"message": "再設定メールを送信しました"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({"message": "必要な情報が不足しています"}), 400
        
    try:
        row = UserRepository.find_reset_token(token)
        if not row:
            return jsonify({"message": "トークンが無効であるか、既に使われています"}), 400
            
        if row['expires_at'] < datetime.now():
            UserRepository.delete_reset_token(token)
            return jsonify({"message": "トークンの有効期限（30分）が切れています"}), 400

        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        UserRepository.update_user_password(row['user_id'], new_password_hash)
        UserRepository.delete_reset_token(token)
        return jsonify({"message": "パスワードを正常に更新しました"}), 200
    except Exception as e:
        return jsonify({"message": f"サーバーエラーが発生しました: {str(e)}"}), 500
