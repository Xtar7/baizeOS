# backend/app/api/v1/completions.py
import logging
from flask import Blueprint, request, jsonify, Response, current_app
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.conversation_store import conversation_store
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

        # ========= 持久化钩子（仅在 conversation_id 存在时启用） =========
        # 老调用（不带 id）persist_conv_id 保持 None → 走零侵入路径。
        # DB 异常被吞掉，聊天照常返回 —— 落库失败绝不可见。
        persist_conv_id = None
        persist_assistant_msg_id = None
        try:
            incoming_cid = data.get("conversation_id")
            if incoming_cid:
                last_user = next(
                    (m for m in reversed(messages) if m.get("role") == "user"),
                    None,
                )
                title = (last_user.get("content", "") if last_user else "")[:60]
                persist_conv_id = conversation_store.get_or_create_for_user_message(
                    incoming_cid,
                    user_id=data.get("user_id", "local"),
                    title=title,
                    kb_id=kb_id,
                )
                if persist_conv_id and last_user:
                    conversation_store.append_user_message(
                        persist_conv_id,
                        last_user.get("content", ""),
                    )
        except Exception as persist_err:
            logger.warning(f"[persist] upsert 失败，继续聊天: {persist_err}")
            persist_conv_id = None

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

            # 落库 assistant（一次性）：占位 + finalize，与流式共用路径
            if persist_conv_id:
                try:
                    choices = result.get("choices") or []
                    content = ""
                    if choices:
                        content = ((choices[0].get("message") or {}).get("content", "") or "")
                    placeholder_id = conversation_store.insert_assistant_placeholder(persist_conv_id)
                    conversation_store.finalize_assistant(
                        msg_id=placeholder_id,
                        content=content,
                        status="complete",
                        usage=result.get("usage"),
                    )
                except Exception as persist_err:
                    logger.warning(f"[persist] 非流式落库失败: {persist_err}")

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

        # 流式 assistant 占位提前建好（同步，<2ms，不影响首字）
        if persist_conv_id:
            try:
                persist_assistant_msg_id = conversation_store.insert_assistant_placeholder(
                    persist_conv_id
                )
            except Exception as persist_err:
                logger.warning(f"[persist] 占位失败: {persist_err}")
                persist_assistant_msg_id = None

        # 累积给后端落库用（闭包变量）
        accumulated_text: list[str] = []
        last_meta: dict = {}

        def generate():
            nonlocal last_meta
            try:
                for chunk in result:

                    if not isinstance(chunk, dict):
                        continue

                    # 保证最基本字段存在（防止下游炸）
                    chunk.setdefault("object", "chat.completion.chunk")

                    # 累计 delta 文本（供 finalize 用）
                    try:
                        choices = chunk.get("choices") or []
                        if choices:
                            delta = (choices[0].get("delta") or {}).get("content")
                            if delta:
                                accumulated_text.append(delta)
                    except Exception:
                        pass

                    # 收尾帧带 usage/references/safety（completions 自定义 done 帧）
                    if chunk.get("done"):
                        last_meta = {
                            "usage": chunk.get("usage"),
                            "references": chunk.get("references"),
                            "safety": chunk.get("safety"),
                        }

                    yield sse_format(chunk)

                # 标准 OpenAI 结束信号
                yield "data: [DONE]\n\n"

            except (GeneratorExit, Exception) as stream_error:
                # 客户端断连/异常 → 标记 interrupted 后再决定要不要 raise
                if persist_assistant_msg_id:
                    try:
                        conversation_store.finalize_assistant(
                            msg_id=persist_assistant_msg_id,
                            content="".join(accumulated_text),
                            status="interrupted",
                            references=last_meta.get("references"),
                            usage=last_meta.get("usage"),
                            safety=last_meta.get("safety"),
                        )
                    except Exception as persist_err:
                        logger.warning(f"[persist] interrupted 落库失败: {persist_err}")

                if isinstance(stream_error, GeneratorExit):
                    # 客户端主动断连（abort/刷新/关闭）→ 让 WSGI 正常关闭
                    raise
                error_payload = {
                    "error": "stream 内部错误",
                    "detail": str(stream_error)
                }
                yield sse_format(error_payload)
                return

            # 正常结束：complete
            if persist_assistant_msg_id:
                try:
                    conversation_store.finalize_assistant(
                        msg_id=persist_assistant_msg_id,
                        content="".join(accumulated_text),
                        status="complete",
                        references=last_meta.get("references"),
                        usage=last_meta.get("usage"),
                        safety=last_meta.get("safety"),
                    )
                except Exception as persist_err:
                    logger.warning(f"[persist] 流式 finalize 失败: {persist_err}")

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