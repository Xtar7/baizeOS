# backend/app/api/v1/tmp/tmp_upload.py
from flask import Blueprint, request, jsonify
from app.services.tmp_service import tmp_service

tmp_upload_bp = Blueprint("tmp_upload", __name__, url_prefix="/v1/files")


@tmp_upload_bp.route("/upload", methods=["POST"])
def upload_tmp_file():
    """
    上传临时文件到指定对话（必须携带 chat_id）
    路径：POST /v1/files/upload
    表单参数：
      - file: 文件（multipart/form-data）
      - chat_id: 当前对话的唯一标识（必填）
    """
    try:
        if "file" not in request.files:
            return jsonify({"error": "未提供文件"}), 400

        file = request.files["file"]
        chat_id = request.form.get("chat_id")

        if not file or file.filename == "":
            return jsonify({"error": "文件名无效"}), 400

        if not chat_id or not chat_id.strip():
            return jsonify({"error": "缺少 chat_id 参数"}), 400

        # 调用 tmp_service 上传（会自动按 chat_id 组织目录）
        result = tmp_service.tmp_upload(
            chat_id=chat_id.strip(),
            file_storage=file
        )

        return jsonify({
            "message": "临时文件上传成功",
            "file": result
        }), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"上传失败: {str(e)}"}), 500