# backend/app/api/v1/tmp/tmp_delete.py
from flask import Blueprint, request, jsonify
from app.services.tmp_service import tmp_service

tmp_delete_bp = Blueprint("tmp_delete", __name__, url_prefix="/v1/files")


@tmp_delete_bp.route("/delete", methods=["POST", "DELETE"])
def delete_tmp_files():
    """
    删除临时文件：支持 POST /v1/files/delete 和 DELETE /v1/files/delete?chat_id=xxx&tmp_file_id=yyy

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

    URL 参数示例（DELETE 友好）：
    DELETE /v1/files/delete?chat_id=chat_xxx&tmp_file_id=abc123
    """
    try:
        # 优先从 URL 参数获取
        chat_id = request.args.get("chat_id")
        tmp_file_id = request.args.get("tmp_file_id")
        tmp_file_ids = request.args.getlist("tmp_file_ids")

        # 如果没有 URL 参数，从 body 获取
        if not chat_id:
            data = request.get_json(silent=True) or {}
            chat_id = data.get("chat_id")
            tmp_file_id = tmp_file_id or data.get("tmp_file_id")
            tmp_file_ids = tmp_file_ids or data.get("tmp_file_ids", [])

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
