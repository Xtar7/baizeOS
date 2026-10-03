# backend/app/api/v1/completions.py
import logging
import time
from flask import Blueprint, request, jsonify, Response, current_app
from app.services.llm_service import llm_service, LLMUnavailableError
from app.services.rag_service import rag_service
from app.services.conversation_store import conversation_store
logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/v1")


def _audit(conv_id, message_id, started_at, model, prompt_name, use_rag, kb_id, data,
           http_status=None, error=None):
    """写一条请求审计；没有 conversation_id 就是未持久化的匿名调用，跳过。"""
    if not conv_id:
        return
    try:
        conversation_store.log_request(
            conversation_id=conv_id,
            message_id=message_id,
            model=model,
            prompt_name=prompt_name,
            use_rag=use_rag,
            kb_id=kb_id,
            stream=True,
            http_status=http_status,
            error=error,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            user_id=(data or {}).get("user_id", "local"),
        )
    except Exception as e:
        logger.warning(f"[audit] 写入失败（忽略）: {e}")


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
        # 模型不可用（显存/内存不足、GGUF 缺失）属于可恢复状态：
        # 返回 503 + 明确文案，前端展示提示而不是笼统的"服务器内部错误"。
        started_at = time.perf_counter()
        try:
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
        except LLMUnavailableError as e:
            logger.warning(f"[chat] 模型不可用: {e}")
            if persist_conv_id:
                conversation_store.log_request(
                    conversation_id=persist_conv_id,
                    model=model,
                    prompt_name=prompt_name,
                    use_rag=use_rag,
                    kb_id=kb_id,
                    stream=stream,
                    http_status=503,
                    error=str(e),
                    duration_ms=int((time.perf_counter() - started_at) * 1000),
                    user_id=data.get("user_id", "local"),
                )
            return jsonify({
                "error": "llm_unavailable",
                "detail": str(e),
                "llm": llm_service.status(),
            }), 503

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
                        # 与流式路径对齐：RAG 的引用与安全元数据同样要落库，
                        # 否则非流式会话重开后引用列表是空的。
                        references=result.get("references"),
                        usage=result.get("usage"),
                        safety=result.get("safety"),
                    )
                    conversation_store.log_request(
                        conversation_id=persist_conv_id,
                        message_id=placeholder_id,
                        model=result.get("model") or model,
                        prompt_name=prompt_name,
                        use_rag=use_rag,
                        kb_id=kb_id,
                        stream=False,
                        http_status=200,
                        duration_ms=int((time.perf_counter() - started_at) * 1000),
                        user_id=data.get("user_id", "local"),
                    )
                except Exception as persist_err:
                    logger.warning(f"[persist] 非流式落库失败: {persist_err}")

            # 统一通过 Flask JSONProvider 输出
            return jsonify(result)

        # ========= 流式 =========
        if not hasattr(result, "__iter__"):
            return jsonify({"error": "流式响应格式异常"}), 500

        # 提前把 json serializer 解引用成普通对象，避免流式生成器
        # 在 GeneratorExit 后调用 current_app 时 app context 已 pop
        app_json_dumps = current_app.json.dumps

        def sse_format(payload: dict) -> str:
            """
            企业级 SSE 格式封装
            统一走 Flask JSONProvider
            """
            return "data: " + app_json_dumps(
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
        saw_done_frame = False
        last_id: str | None = None
        last_usage: dict | None = None

        def generate():
            nonlocal last_meta, saw_done_frame, last_id, last_usage
            try:
                for chunk in result:

                    if not isinstance(chunk, dict):
                        continue

                    # 保证最基本字段存在（防止下游炸）
                    chunk.setdefault("object", "chat.completion.chunk")

                    # 服务层的收尾 chunk 把 usage 放在顶层而不是 done 帧里，
                    # 这里顺手留档，补 done 帧时回填
                    if chunk.get("usage"):
                        last_usage = chunk.get("usage")
                    if chunk.get("id"):
                        last_id = chunk.get("id")

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
                        saw_done_frame = True
                        # RAG 路径的 done 帧 usage 为 null（真实值在它前一个
                        # chunk 的顶层），这里回填，避免 usage 永久丢失。
                        last_meta = {
                            "usage": chunk.get("usage") or last_usage,
                            "references": chunk.get("references"),
                            "safety": chunk.get("safety"),
                        }
                        # 同样回填给客户端，前端的实时 token 统计才有值
                        if not chunk.get("usage") and last_usage:
                            chunk["usage"] = last_usage

                    yield sse_format(chunk)

                # 服务层若没自己产出 done 帧，这里补一个。
                # 契约（docs/API调用方案.md 3.3）要求 done 帧先于 [DONE]：
                # 前端靠它清掉 streaming 标志并回填 usage/references/safety，
                # 缺了它前端会永远停在"生成中"，发不出第二条消息。
                if not saw_done_frame:
                    usage = last_meta.get("usage") or last_usage
                    yield sse_format({
                        "id": last_id or "chatcmpl-stream",
                        "object": "chat.completion.chunk",
                        "done": True,
                        "usage": usage,
                        "references": last_meta.get("references") or [],
                        "safety": last_meta.get("safety"),
                    })
                    # 补出来的 usage 也要进 last_meta，否则下面的 finalize
                    # 落库时 usage 为空，前端重开会话看不到 token 统计。
                    last_meta = {
                        "usage": usage,
                        "references": last_meta.get("references") or [],
                        "safety": last_meta.get("safety"),
                    }

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
                    _audit(persist_conv_id, persist_assistant_msg_id, started_at,
                           model, prompt_name, use_rag, kb_id, data,
                           http_status=None, error="client_disconnected")
                    raise
                error_payload = {
                    "error": "stream 内部错误",
                    "detail": str(stream_error)
                }
                _audit(persist_conv_id, persist_assistant_msg_id, started_at,
                       model, prompt_name, use_rag, kb_id, data,
                       http_status=500, error=str(stream_error))
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

            _audit(persist_conv_id, persist_assistant_msg_id, started_at,
                   model, prompt_name, use_rag, kb_id, data, http_status=200)

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