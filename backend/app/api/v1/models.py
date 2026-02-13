# app/api/v1/models.py
from flask import Blueprint, jsonify
import time

from app.services.llm_service import llm_service

models_bp = Blueprint("openai_models", __name__, url_prefix="/v1")


@models_bp.route("/models", methods=["GET"])
def list_models():
    model_list = []

    created = int(time.time())

    for model_path in llm_service.models:
        model_id = model_path.stem

        model_list.append({
            "id": model_id,
            "object": "model",
            "created": created,
            "owned_by": "local"
        })

    return jsonify({
        "object": "list",
        "data": model_list
    })