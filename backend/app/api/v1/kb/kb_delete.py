# backend/app/api/v1/kb/kb_delete.py
from flask import Blueprint, request, jsonify
from app.services.kb_service import kb_service

kb_delete_bp = Blueprint("kb_delete", __name__, url_prefix="/v1/kb")


# ==================== 删除知识库（支持批量）====================

@kb_delete_bp.route("", methods=["DELETE", "POST"])
def delete_kb():
    """
    删除知识库：支持 DELETE /v1/kb?kb_id=xxx 和 POST /v1/kb {kb_id: "xxx"}
    Body: {"kb_id": "xxx"} 或 {"kb_ids": ["xxx", "yyy"]}
    Query: ?kb_id=xxx 或 ?kb_ids=xxx&kb_ids=yyy
    """
    # 优先从 URL 参数获取（DELETE 友好）
    kb_id = request.args.get("kb_id")
    kb_ids = request.args.getlist("kb_ids")

    # 如果没有 URL 参数，从 body 获取
    if not kb_id and not kb_ids:
        data = request.get_json(silent=True) or {}
        kb_id = data.get("kb_id")
        kb_ids = data.get("kb_ids", [])

    # 单条删除
    if kb_id:
        ok = kb_service.delete(kb_id)
        if not ok:
            return jsonify({"error": "知识库不存在"}), 404
        return jsonify({
            "deleted_count": 1,
            "kb_ids": [kb_id],
            "deleted": True
        })

    # 批量删除
    if kb_ids:
        if not isinstance(kb_ids, list):
            return jsonify({"error": "kb_ids 必须是数组"}), 400
        if len(kb_ids) == 0:
            return jsonify({"error": "kb_ids 不能为空数组"}), 400

        deleted = []
        failed = []
        for kid in kb_ids:
            try:
                ok = kb_service.delete(kid)
                if ok:
                    deleted.append(kid)
                else:
                    failed.append({"kb_id": kid, "reason": "知识库不存在"})
            except Exception as e:
                failed.append({"kb_id": kid, "reason": str(e)})

        return jsonify({
            "deleted_count": len(deleted),
            "kb_ids": deleted,
            "failed": failed,
            "deleted": len(failed) == 0
        })

    return jsonify({"error": "缺少 kb_id 或 kb_ids 参数"}), 400


# ==================== 删除文件（支持批量）====================

@kb_delete_bp.route("/files", methods=["DELETE", "POST"])
def delete_files():
    """
    删除文件：支持 DELETE /v1/kb/files?kb_id=xxx&kb_file_id=yyy 和 POST /v1/kb/files
    Body:
      - 单条: {"kb_id": "xxx", "kb_file_id": "yyy"}
      - 批量: {"kb_id": "xxx", "kb_file_ids": ["yyy", "zzz"]}
    """
    # 优先从 URL 参数获取（DELETE 友好）
    kb_id = request.args.get("kb_id")
    kb_file_id = request.args.get("kb_file_id")
    kb_file_ids = request.args.getlist("kb_file_ids")

    # 如果没有 URL 参数，从 body 获取
    if not kb_id:
        data = request.get_json(silent=True) or {}
        kb_id = data.get("kb_id")
        kb_file_id = kb_file_id or data.get("kb_file_id")
        kb_file_ids = kb_file_ids or data.get("kb_file_ids", [])

    if not kb_id:
        return jsonify({"error": "缺少 kb_id 参数"}), 400

    # 单条删除
    if kb_file_id:
        try:
            result = kb_service.delete_file(kb_id, kb_file_id)
            return jsonify(result)
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 500

    # 批量删除
    if kb_file_ids:
        if not isinstance(kb_file_ids, list):
            return jsonify({"error": "kb_file_ids 必须是数组"}), 400
        if len(kb_file_ids) == 0:
            return jsonify({"error": "kb_file_ids 不能为空数组"}), 400

        try:
            result = kb_service.batch_delete_files(kb_id, kb_file_ids)
            return jsonify(result)
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "缺少 kb_file_id 或 kb_file_ids 参数"}), 400
