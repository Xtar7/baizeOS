# backend/app/api/v1/kb/kb_delete.py
from flask import Blueprint, jsonify
from app.services.kb_service import kb_service

kb_delete_bp = Blueprint("kb_delete", __name__, url_prefix="/v1/kb")

@kb_delete_bp.route("/<kb_name>", methods=["DELETE"])
def delete_kb(kb_name):
    ok = kb_service.tmp_delete(kb_name)
    if not ok:
        return jsonify({"error": "kb not found"}), 404

    return jsonify({
        "id": kb_name,
        "deleted": True
    })

