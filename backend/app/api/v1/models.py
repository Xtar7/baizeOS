# app/api/v1/models.py

from flask import Blueprint, jsonify
import time

from app.services.llm_service import llm_service

models_bp = Blueprint("models", __name__, url_prefix="/v1")


@models_bp.route("/models", methods=["GET"])
def list_models():
    model_list = []

    for model_name in llm_service.models.keys():
        model_list.append({
            "id": model_name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "local",
        })

    return jsonify({
        "object": "list",
        "data": model_list
    })