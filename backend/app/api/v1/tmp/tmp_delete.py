# backend/app/api/v1/tmp/tmp_delete.py
from flask import Blueprint, request, jsonify
from app.services.tmp_service import tmp_service

tmp_delete_bp = Blueprint("tmp_delete", __name__, url_prefix="/v1/files")


@tmp_delete_bp.route("/delete", methods=["POST"])
def delete_tmp_files():
    """
    删除临时文件（必须同时提供 chat_id 和 tmp_file_id / tmp_file_ids）

    POST /v1/files/delete

    Body 示例：
    单个文件：
    {
      "chat_id": "chat_xxx",
      "tmp_file_id": "64e82eb0d7e3458a834aa5f86374806a"
    }

    批量删除：
    {
      "chat_id": "chat_xxx",
      "tmp_file_ids": ["id1", "id2", "id3"]
    }
    """
    try:
        data = request.get_json(silent=True) or {}

        chat_id = data.get("chat_id")
        tmp_file_id = data.get("tmp_file_id")
        tmp_file_ids = data.get("tmp_file_ids")

        if not chat_id or not isinstance(chat_id, str) or not chat_id.strip():
            return jsonify({"error": "必须提供有效的 chat_id"}), 400

        chat_id = chat_id.strip()

        deleted_count = 0

        # 优先处理批量删除
        if tmp_file_ids:
            if not isinstance(tmp_file_ids, list):
                return jsonify({"error": "tmp_file_ids 必须是数组"}), 400

            for fid in tmp_file_ids:
                if not isinstance(fid, str) or not fid.strip():
                    continue
                if tmp_service.delete_file(chat_id, fid.strip()):
                    deleted_count += 1

        # 单个删除
        elif tmp_file_id:
            if not isinstance(tmp_file_id, str) or not tmp_file_id.strip():
                return jsonify({"error": "tmp_file_id 无效"}), 400

            if tmp_service.delete_file(chat_id, tmp_file_id.strip()):
                deleted_count += 1

        else:
            return jsonify({"error": "必须提供 tmp_file_id 或 tmp_file_ids"}), 400

        return jsonify({
            "chat_id": chat_id,
            "deleted_count": deleted_count,
            "message": f"成功删除 {deleted_count} 个临时文件"
        })

    except Exception as e:
        return jsonify({"error": f"删除失败: {str(e)}"}), 500