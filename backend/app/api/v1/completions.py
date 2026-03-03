# backend/app/api/v1/completions.py
from flask import Blueprint, request, jsonify, Response
import json
import time
import uuid

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

chat_bp = Blueprint("chat", __name__, url_prefix="/v1")


@chat_bp.route("/chat/completions", methods=["POST"])
def chat_completions():
    try:
        data = request.get_json() or {}

        debug = data.get("debug", False)

        messages = data.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "messages 必须是非空数组"}), 400

        stream = data.get("stream", False)
        model = data.get("model") or "default-model"  # 可设置默认值
        prompt_name = data.get("prompt", "default")

        # RAG 参数
        use_rag = data.get("rag", False)
        kb_id = data.get("kb_id")

        completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created_time = int(time.time())

        if not stream:
            # 非流式
            if use_rag and kb_id:
                result = rag_service.rag_chat(
                    messages=messages,
                    kb_id=kb_id,
                    stream=False,
                    debug=debug,
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
                "model": result.get("model", model),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.get("content", "")
                        },
                        "finish_reason": result.get("finish_reason", "stop"),
                    }
                ],
                "usage": result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
                "system_fingerprint": None,  # 可选，后续可加模型指纹
                "references": result.get("references", [])  # 新增：references
            })

        # 流式响应
        def generate():
            if use_rag and kb_id:
                token_stream = rag_service.rag_chat(
                    messages=messages,
                    kb_id=kb_id,
                    stream=True,
                    debug=debug,
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

            final_usage = None
            references = None  # 新增：references

            for chunk in token_stream:
                if isinstance(chunk, dict) and "done" in chunk:
                    # 最后一块，带 usage 和 references
                    final_usage = chunk.get("usage")
                    references = chunk.get("references", [])  # 新增
                    yield f"data: {json.dumps({
                        'id': completion_id,
                        'object': 'chat.completion.chunk',
                        'created': created_time,
                        'model': model,
                        'choices': [{
                            'index': 0,
                            'delta': {},
                            'finish_reason': 'stop'
                        }],
                        'usage': final_usage,
                        'references': references  # 新增：但stream通常不带顶层references，可调整为最后一块带
                    }, ensure_ascii=False)}\n\n"
                    break

                # 普通 chunk
                delta_content = chunk.get("delta", "") if isinstance(chunk, dict) else str(chunk)
                yield f"data: {json.dumps({
                    'id': completion_id,
                    'object': 'chat.completion.chunk',
                    'created': created_time,
                    'model': model,
                    'choices': [{
                        'index': 0,
                        'delta': {'content': delta_content},
                        'finish_reason': None
                    }]
                }, ensure_ascii=False)}\n\n"

            # 结束标志
            yield "data: [DONE]\n\n"

        return Response(generate(), mimetype="text/event-stream")

    except ValueError as ve:
        return jsonify({"error": f"参数错误: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500