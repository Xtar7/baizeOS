# backend/app/api/v1/tmp/tmp_list.py
from flask import Blueprint, request, jsonify
from app.services.tmp_service import tmp_service

tmp_list_bp = Blueprint("tmp_list", __name__, url_prefix="/v1/files")


@tmp_list_bp.route("/list", methods=["POST"])
def list_tmp_files():
    """
    列出临时文件（必须提供 chat_id）
    POST /v1/files/list
    Body: { "chat_id": "chat_xxx" }
    """
    try:
        data = request.get_json(silent=True) or {}
        chat_id = data.get("chat_id")

        if not chat_id or not isinstance(chat_id, str) or not chat_id.strip():
            return jsonify({"error": "必须提供有效的 chat_id"}), 400

        files = tmp_service.tmp_list(chat_id=chat_id.strip())

        # 按时间倒序（新文件在前）
        files_sorted = sorted(files, key=lambda x: x.get("created_at", 0), reverse=True)

        return jsonify({
            "object": "list",
            "chat_id": chat_id,
            "total": len(files_sorted),
            "data": files_sorted
        })

    except ValueError as ve:
        return jsonify({"error": f"参数错误: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"error": f"获取列表失败: {str(e)}"}), 500