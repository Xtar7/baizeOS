# backend/app/api/v1/kb/kb_get1.py
from flask import Blueprint, jsonify
from app.services.kb_service import kb_service

kb_get_bp = Blueprint("kb_get", __name__, url_prefix="/v1/kb")


@kb_get_bp.route("/<kb_id>", methods=["GET"])
def get_kb(kb_id):
    """获取单个知识库详情"""
    try:
        meta = kb_service.get(kb_id)
        if not meta:
            return jsonify({"error": "知识库不存在"}), 404
        return jsonify(meta)
    except Exception as e:
        return jsonify({"error": str(e)}), 500