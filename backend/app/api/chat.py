from flask import Blueprint, request, jsonify, Response
import json
from app.services.llm_service import llm_service

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    stream = data.get("stream", False)
    prompt_name = data.get("prompt", "default")

    if not stream:
        reply = llm_service.chat(
            messages=messages,
            stream=False,
            prompt_name=prompt_name
        )

        return jsonify({
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": reply
                    }
                }
            ]
        })

    def generate():
        token_stream = llm_service.chat(
            messages=messages,
            stream=True,
            prompt_name=prompt_name
        )

        for token in token_stream:
            data = {
                "choices": [
                    {
                        "delta": {
                            "content": token
                        }
                    }
                ]
            }

            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")