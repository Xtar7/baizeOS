# backend/app/api/v1/tmp/tmp_delete.py
from flask import Blueprint, request, jsonify
from app.services.tmp_service import tmp_service

tmp_delete_bp = Blueprint("tmp_delete", __name__, url_prefix="/v1/files")


@tmp_delete_bp.route("/<file_id>", methods=["DELETE"])
def delete_tmp_file(file_id):
    """删除单个临时文件"""
    ok = tmp_service.tmp_delete(file_id)
    if not ok:
        return jsonify({"error": "临时文件不存在或已被删除"}), 404

    return jsonify({
        "id": file_id,
        "object": "file",
        "deleted": True
    })


@tmp_delete_bp.route("/", methods=["DELETE"])
def delete_tmp_by_chat():
    """按 chat_id 批量删除某个对话的所有临时文件"""
    data = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")

    if not chat_id:
        return jsonify({"error": "缺少 chat_id 参数"}), 400

    count = tmp_service.tmp_delete_by_chat(chat_id)

    return jsonify({
        "chat_id": chat_id,
        "deleted_count": count,
        "message": f"已删除 {count} 个临时文件"
    })