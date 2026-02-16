# backend/app/api/v1/kb/kb_update.py
from flask import Blueprint, request, jsonify
from app.services.kb_service import kb_service

kb_update_bp = Blueprint("kb_update", __name__, url_prefix="/v1/kb")


@kb_update_bp.route("/<kb_id>/rename", methods=["POST"])
def rename_kb(kb_id):
    """重命名：POST /v1/kb/<uuid>/rename + { "display_name": "新名字" }"""
    data = request.get_json() or {}
    new_display_name = data.get("display_name")

    if not new_display_name:
        return jsonify({"error": "缺少 display_name 参数"}), 400

    try:
        meta = kb_service.rename(kb_id, new_display_name)
        return jsonify(meta)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@kb_update_bp.route("/<kb_id>/prompt", methods=["PATCH"])
def update_prompt(kb_id):
    """更新 prompt：PATCH /v1/kb/<uuid>/prompt + { "system_prompt": "..." }"""
    data = request.get_json() or {}
    system_prompt = data.get("system_prompt", "")

    try:
        meta = kb_service.update_prompt(kb_id, system_prompt)
        return jsonify(meta)
    except Exception as e:
        return jsonify({"error": str(e)}), 400