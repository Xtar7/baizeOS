# backend/app/api/chat.py
from flask import Blueprint, request, jsonify

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    # 临时测试回复
    reply = f"收到你的问题：{user_message}"

    return jsonify({
        "reply": reply
    })
