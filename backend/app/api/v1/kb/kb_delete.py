# backend/app/api/v1/kb/kb_delete.py
from flask import Blueprint, request, jsonify
from app.services.kb_service import kb_service

kb_delete_bp = Blueprint("kb_delete", __name__, url_prefix="/v1/kb")


@kb_delete_bp.route("/<kb_id>", methods=["DELETE"])
def delete_kb(kb_id):
    """RESTful 删除：DELETE /v1/kb/<uuid>"""
    ok = kb_service.delete(kb_id)
    if not ok:
        return jsonify({"error": "知识库不存在"}), 404

    return jsonify({
        "id": kb_id,
        "deleted": True
    })


@kb_delete_bp.route("/", methods=["DELETE"])
def delete_kb_from_body():
    """兼容 body 删除：DELETE /v1/kb/ + { "id": "uuid..." }"""
    data = request.get_json(silent=True) or {}
    kb_id = data.get("id")

    if not kb_id:
        return jsonify({"error": "缺少 id 参数"}), 400

    ok = kb_service.delete(kb_id)
    if not ok:
        return jsonify({"error": "知识库不存在"}), 404

    return jsonify({
        "id": kb_id,
        "deleted": True
    })