# app/api/v1/chat.py
from flask import Blueprint, request, jsonify, Response
import json
import time
import uuid

from app.services.llm_service import llm_service

chat_bp = Blueprint("openai_chat", __name__, url_prefix="/v1")


def generate_id():
    return "chatcmpl-" + uuid.uuid4().hex[:24]


@chat_bp.route("/chat/completions", methods=["POST"])
def chat_completions():
    data = request.json or {}

    messages = data.get("messages", [])
    model = data.get("model")
    stream = data.get("stream", False)
    model = data.get("model", "local-model")
    prompt_name = data.get("prompt", "default")

    completion_id = generate_id()
    created = int(time.time())

    # -----------------------
    # 非流式
    # -----------------------
    if not stream:
        reply = llm_service.completions(
            model=model,
            messages=messages,
            stream=False,
            prompt_name=prompt_name
        )

        return jsonify({
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": reply
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        })

    # -----------------------
    # 流式
    # -----------------------
    def generate():
        token_stream = llm_service.completions(
            model=model,
            messages=messages,
            stream=True,
            prompt_name=prompt_name
        )

        for token in token_stream:
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": token
                        },
                        "finish_reason": None
                    }
                ]
            }

            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        # 结束帧
        end_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }

        yield f"data: {json.dumps(end_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")