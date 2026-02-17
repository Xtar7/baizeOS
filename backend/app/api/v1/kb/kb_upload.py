# backend/app/api/v1/kb/kb_upload.py
from flask import Blueprint, request, jsonify
from app.services.upload_service import upload_service

kb_upload_bp = Blueprint("kb_upload", __name__, url_prefix="/v1/kb")

@kb_upload_bp.route("/upload", methods=["POST"])
def upload_to_kb():
    try:
        if "file" not in request.files:
            return jsonify({"error": "未提供文件"}), 400

        file = request.files["file"]
        kb_id = request.form.get("kb_id")

        if not file or file.filename == "":
            return jsonify({"error": "文件名无效"}), 400

        if not kb_id:
            return jsonify({"error": "缺少 kb_id 参数"}), 400

        # 直接调用并返回 upload_service 的结果
        result = upload_service.save_and_index(file, kb_id=kb_id)

        return jsonify({
            "message": "上传成功",
            "kb_id": kb_id,
            "file_info": result   # 这里 result 已经包含 kb_file_id 等字段
        }), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"上传失败: {str(e)}"}), 500