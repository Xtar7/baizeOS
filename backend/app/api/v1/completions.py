# backend/app/api/v1/completions.py
import logging
from flask import Blueprint, request, jsonify, Response, current_app
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/v1")


@chat_bp.route("/chat/completions", methods=["POST"])
def chat_completions():
    try:
        data = request.get_json(silent=True) or {}

        # ========= 参数校验 =========
        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            return jsonify({"error": "messages 必须是非空数组"}), 400

        stream = bool(data.get("stream", False))
        model = data.get("model")
        prompt_name = data.get("prompt", "default")
        use_rag = bool(data.get("rag", False))
        kb_id = data.get("kb_id")
        debug = bool(data.get("debug", False))

        # ========= 调用服务层 =========
        if use_rag and kb_id:
            result = rag_service.rag_chat(
                messages=messages,
                kb_id=kb_id,
                stream=stream,
                debug=debug,
                model=model,
                prompt_name=prompt_name,
            )
        else:
            result = llm_service.chat_completions(
                messages=messages,
                stream=stream,
                model=model,
                prompt_name=prompt_name,
            )

        # ========= 非流式 =========
        if not stream:
            if not isinstance(result, dict):
                return jsonify({"error": "响应格式异常"}), 500

            # 统一通过 Flask JSONProvider 输出
            return jsonify(result)

        # ========= 流式 =========
        if not hasattr(result, "__iter__"):
            return jsonify({"error": "流式响应格式异常"}), 500

        def sse_format(payload: dict) -> str:
            """
            企业级 SSE 格式封装
            统一走 Flask JSONProvider
            """
            return "data: " + current_app.json.dumps(
                payload,
                ensure_ascii=False
            ) + "\n\n"

        def generate():
            try:
                for chunk in result:

                    if not isinstance(chunk, dict):
                        continue

                    # 保证最基本字段存在（防止下游炸）
                    chunk.setdefault("object", "chat.completion.chunk")

                    yield sse_format(chunk)

                # 标准 OpenAI 结束信号
                yield "data: [DONE]\n\n"

            except Exception as stream_error:
                error_payload = {
                    "error": "stream 内部错误",
                    "detail": str(stream_error)
                }
                yield sse_format(error_payload)

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        import traceback
        logger.error(f"chat_completions 异常: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "error": "服务器内部错误",
            "detail": str(e)
        }), 500