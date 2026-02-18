# app/api/v1/rag/llm_list.py （新建 blueprint 或加到现有路由）

from flask import Blueprint, jsonify
from app.services.embedding_service import get_available_embedding_models, DEFAULT_MODEL_NAME

rag_models_bp = Blueprint("rag_models", __name__, url_prefix="/v1/rag")

@rag_models_bp.route("/embedding/models", methods=["GET"])
def list_embedding_models():
    models = get_available_embedding_models()
    return jsonify({
        "models": models,
        "default": DEFAULT_MODEL_NAME,
        "total": len(models)
    }), 200