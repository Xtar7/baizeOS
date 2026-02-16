# backend/app/api/v1/kb/kb_upload.py
from flask import Blueprint, request, jsonify
from app.services.upload_service import upload_service

kb_bp = Blueprint("kb_upload", __name__, url_prefix="/v1/kb")


@kb_bp.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "未提供文件"}), 400

        file = request.files["file"]
        kb_id = request.form.get("kb_id")

        if not file or file.filename == "":
            return jsonify({"error": "文件名无效"}), 400

        kb_id = upload_service.save_and_index(file, kb_id=kb_id)

        return jsonify({
            "message": "上传成功",
            "kb_id": kb_id
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 400