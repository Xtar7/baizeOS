# backend/app/api/v1/kb/kb_create.py
from flask import Blueprint, request, jsonify
from app.services.kb_service import kb_service

kb_create_bp = Blueprint("kb_create", __name__, url_prefix="/v1/kb")

@kb_create_bp.route("/", methods=["POST"])
def create_kb():
    data = request.json or {}
    name = data.get("name")
    system_prompt = data.get("system_prompt", "")

    if not name:
        return jsonify({"error": "missing kb name"}), 400

    try:
        meta = kb_service.create(name, system_prompt)
        return jsonify(meta)
    except Exception as e:
        return jsonify({"error": str(e)}), 400