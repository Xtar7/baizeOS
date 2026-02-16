# backend/app/api/v1/tmp/tmp_upload.py
from flask import Blueprint, request, jsonify
from app.services.tmp_service import tmp_service

tmp_upload_bp = Blueprint("tmp_upload", __name__, url_prefix="/v1/files")

@tmp_upload_bp.route("/", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "缺少文件"}), 400

    file = request.files["file"]

    try:
        result = tmp_service.upload(file)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400