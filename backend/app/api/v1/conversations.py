# backend/app/api/v1/conversations.py
"""会话账本 REST 端点 —— GET/POST/PATCH/DELETE。

兼容老调用：老前端不带 conversation_id 调 chat/completions 时本蓝图不参与。
"""
from __future__ import annotations

import logging
from flask import Blueprint, request, jsonify

from app.services.conversation_store import conversation_store

logger = logging.getLogger(__name__)

conversations_bp = Blueprint("conversations", __name__, url_prefix="/v1/conversations")


def _err(msg: str, status: int = 400, detail: str | None = None):
    payload = {"error": msg}
    if detail is not None:
        payload["detail"] = detail
    return jsonify(payload), status


@conversations_bp.route("", methods=["GET"])
def list_():
    """GET /v1/conversations?user_id=local&limit=200"""
    user_id = request.args.get("user_id", "local")
    try:
        limit = max(1, min(500, int(request.args.get("limit", "200"))))
    except ValueError:
        return _err("limit 必须是整数")
    items = conversation_store.list_conversations(user_id=user_id, limit=limit)
    return jsonify({"object": "list", "data": items, "total": len(items)}), 200


@conversations_bp.route("", methods=["POST"])
def create():
    """POST /v1/conversations  body: {title?, kb_id?, conversation_id?, user_id?}"""
    data = request.get_json(silent=True) or {}
    conv_id = data.get("conversation_id") or conversation_store.new_id()
    try:
        conv_id = conversation_store.upsert_conversation(
            conv_id=conv_id,
            user_id=data.get("user_id", "local"),
            title=str(data.get("title", ""))[:120],
            kb_id=data.get("kb_id"),
        )
    except Exception as e:
        logger.exception("create conversation failed")
        return _err("create failed", 500, detail=str(e))
    return jsonify(conversation_store.get_conversation(conv_id)), 201


@conversations_bp.route("/<conv_id>", methods=["GET"])
def get_one(conv_id: str):
    """GET /v1/conversations/{id}?include_messages=true"""
    conv = conversation_store.get_conversation(conv_id)
    if not conv:
        return _err("conversation not found", 404)
    if request.args.get("include_messages", "false").lower() == "true":
        conv["messages"] = conversation_store.list_messages(conv_id)
    return jsonify(conv), 200


@conversations_bp.route("/<conv_id>", methods=["PATCH"])
def patch(conv_id: str):
    """PATCH /v1/conversations/{id}  body: {title?}"""
    if not conversation_store.get_conversation(conv_id):
        return _err("conversation not found", 404)
    data = request.get_json(silent=True) or {}
    if "title" in data:
        try:
            conversation_store.update_conversation_title(conv_id, str(data["title"])[:120])
        except Exception as e:
            return _err("update title failed", 500, detail=str(e))
    return jsonify(conversation_store.get_conversation(conv_id)), 200


@conversations_bp.route("/<conv_id>", methods=["DELETE"])
def delete(conv_id: str):
    """DELETE /v1/conversations/{id}  软删"""
    if not conversation_store.soft_delete_conversation(conv_id):
        return _err("conversation not found", 404)
    return jsonify({"deleted": True, "id": conv_id}), 200
