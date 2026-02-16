# backend/app/api/v1/tmp/tmp_list.py
from flask import Blueprint, jsonify
from app.services.tmp_service import tmp_service

tmp_list_bp = Blueprint("tmp_list", __name__, url_prefix="/v1/files")

@tmp_list_bp.route("/list", methods=["GET"])
def list_files():
    files = tmp_service.tmp_list()
    return jsonify({
        "object": "list",
        "data": files
    })