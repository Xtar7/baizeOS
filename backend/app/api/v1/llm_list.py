# backend/app/api/v1/llm_list.py
"""GET /v1/models —— OpenAI 兼容的模型列表。

即使当前没有模型成功加载也要正常返回（列表来自目录扫描），
附带 loaded 标记，让设置页能区分"没发现模型"和"发现了但没装上"。
"""
from flask import Blueprint, jsonify
import time

from app.services.llm_service import llm_service

llm_list_bp = Blueprint("models", __name__, url_prefix="/v1")


@llm_list_bp.route("/models", methods=["GET"])
def list_models():
    created = int(time.time())
    model_list = [
        {
            "id": name,
            "object": "model",
            "created": created,
            "owned_by": "local",
            "loaded": name == llm_service.active_model_name,
        }
        for name in llm_service.models.keys()
    ]

    return jsonify({
        "object": "list",
        "data": model_list,
        "active": llm_service.active_model_name,
        "available": llm_service.available,
        "error": llm_service.load_error,
    })
