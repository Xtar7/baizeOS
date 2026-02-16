# backend/app/api/v1/tmp/tmp_delete.py
from flask import Blueprint, jsonify
from app.services.tmp_service import tmp_service

tmp_delete_bp = Blueprint("tmp_delete", __name__, url_prefix="/v1/files")

@tmp_delete_bp.route("/<tmp_name>", methods=["DELETE"])
def delete_tmp(tmp_name):
    ok = tmp_service.tmp_delete(tmp_name)
    if not ok:
        return jsonify({"error": "kb not found"}), 404

    return jsonify({
        "id": tmp_name,
        "deleted": True
    })
