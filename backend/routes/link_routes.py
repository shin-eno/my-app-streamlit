import logging
from flask import Blueprint, request, jsonify
from repository.link_repository import LinkRepository

link_bp = Blueprint('links', __name__)
logger = logging.getLogger(__name__)

@link_bp.route('/api/links', methods=['GET'])
def get_links():
    try:
        links = LinkRepository.get_all_active_links()
        return jsonify(links), 200
    except Exception as e:
        logger.error(f"リンク集の取得失敗: {e}", exc_info=True)
        return jsonify({"message": "取得エラー"}), 500

@link_bp.route('/api/links', methods=['POST'])
def add_link():
    data = request.json or {}
    try:
        LinkRepository.create_link(
            data.get('site_name'), data.get('url'), data.get('category'),
            data.get('display_order', 10), data.get('description')
        )
        return jsonify({"message": "登録に成功しました"}), 201
    except Exception as e:
        logger.error(f"リンク登録失敗: {e}", exc_info=True)
        return jsonify({"message": "登録エラー"}), 500

@link_bp.route('/api/links/<int:link_id>', methods=['PUT'])
def edit_link(link_id):
    data = request.json or {}
    try:
        LinkRepository.update_link(
            link_id, data.get('site_name'), data.get('url'), data.get('category'),
            data.get('display_order'), data.get('description')
        )
        return jsonify({"message": "更新に成功しました"}), 200
    except Exception as e:
        logger.error(f"リンク更新失敗: {e}", exc_info=True)
        return jsonify({"message": "更新エラー"}), 500

@link_bp.route('/api/links/<int:link_id>', methods=['DELETE'])
def delete_link(link_id):
    try:
        LinkRepository.soft_delete_link(link_id)
        return jsonify({"message": "論理削除に成功しました"}), 200
    except Exception as e:
        logger.error(f"リンク削除失敗: {e}", exc_info=True)
        return jsonify({"message": "削除エラー"}), 500