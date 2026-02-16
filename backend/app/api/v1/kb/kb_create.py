# backend/app/api/v1/kb/kb_create.py
from flask import Blueprint, request, jsonify
from app.services.kb_service import kb_service

kb_create_bp = Blueprint("kb_create", __name__, url_prefix="/v1/kb")

@kb_create_bp.route("/", methods=["POST"])
def create_kb():
    data = request.json or {}
    display_name = data.get("display_name")
    system_prompt = data.get("system_prompt", "")
    description = data.get("description", "")

    if not display_name or not display_name.strip():
        return jsonify({"error": "缺少或无效的 display_name"}), 400

    try:
        meta = kb_service.create(
            display_name=display_name.strip(),
            system_prompt=system_prompt,
            description=description
        )
        return jsonify(meta), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"创建失败: {str(e)}"}), 500