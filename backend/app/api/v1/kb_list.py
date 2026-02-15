# app/api/v1/kb_list.py

from flask import Blueprint, jsonify
from app.config.settings import KB_DIR

kb_list_bp = Blueprint("kb_list", __name__, url_prefix="/v1/kb")


@kb_list_bp.route("/list", methods=["GET"])
def list_kb():
    kb_list = []

    if not KB_DIR.exists():
        return jsonify({"data": []})

    for kb_dir in KB_DIR.iterdir():
        if not kb_dir.is_dir():
            continue

        kb_list.append({
            "kb_id": kb_dir.name,
            "path": str(kb_dir),
        })

    return jsonify({
        "object": "list",
        "data": kb_list
    })