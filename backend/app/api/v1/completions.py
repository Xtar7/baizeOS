# app/api/v1/completions.py
from flask import Blueprint, request, jsonify, Response
import json
import time
import uuid

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

chat_bp = Blueprint("chat", __name__, url_prefix="/v1/chat")


@chat_bp.route("/completions", methods=["POST"])
def chat_completions():
    data = request.json or {}

    messages = data.get("messages", [])
    stream = data.get("stream", False)
    model = data.get("model")
    prompt_name = data.get("prompt", "default")

    # RAG 参数
    rag = data.get("rag", False)
    kb_id = data.get("kb_id")

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created_time = int(time.time())

    # =========================
    # 非流式
    # =========================
    if not stream:
        if rag:
            result = rag_service.rag_chat(
                messages=messages,
                kb_id=kb_id,
                stream=False,
                model=model,
                prompt_name=prompt_name,
            )
        else:
            result = llm_service.chat_completions(
                messages=messages,
                stream=False,
                model=model,
                prompt_name=prompt_name,
            )

        return jsonify({
            "id": completion_id,
            "object": "chat.completion",
            "created": created_time,
            "model": result["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result["content"],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": result["usage"],
        })

    # =========================
    # 流式
    # =========================
    def generate():
        if rag:
            token_stream = rag_service.rag_chat(
                messages=messages,
                kb_id=kb_id,
                stream=True,
                model=model,
                prompt_name=prompt_name,
            )
        else:
            token_stream = llm_service.chat_completions(
                messages=messages,
                stream=True,
                model=model,
                prompt_name=prompt_name,
            )

        for chunk in token_stream:
            # 最终 usage 包
            if "done" in chunk:
                data_obj = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": chunk["model"],
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": chunk["usage"],
                }
                yield f"data: {json.dumps(data_obj, ensure_ascii=False)}\n\n"
                break

            # 普通 token
            data_obj = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": chunk["delta"]
                        },
                        "finish_reason": None,
                    }
                ],
            }

            yield f"data: {json.dumps(data_obj, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")