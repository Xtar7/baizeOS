# backend/app/api/v1/eb_list.py
from flask import Blueprint, jsonify
from app.services.embedding_factory import get_available_embedding_models, DEFAULT_MODEL_NAME

rag_models_bp = Blueprint("rag_models", __name__, url_prefix="/v1/rag")


@rag_models_bp.route("/embedding_models", methods=["GET"])
def list_embedding_models():
    """列出所有可用的 embedding 模型"""
    models = get_available_embedding_models()
    return jsonify({
        "models": models,
        "default": DEFAULT_MODEL_NAME,
        "total": len(models)
    }), 200
