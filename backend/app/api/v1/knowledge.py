# app/api/v1/kb.py
from flask import Blueprint, request, jsonify
from app.services.upload_service import upload_service

kb_bp = Blueprint("kb", __name__, url_prefix="/v1/kb")


@kb_bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    file = request.files["file"]

    try:
        file_id = upload_service.save_and_index(file)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "file_id": file_id,
        "status": "indexed"
    })