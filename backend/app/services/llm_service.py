# backend/app/services/llm_service.py
import time
from pathlib import Path
from typing import List, Dict, Any, Generator
from app.config.settings import (
    LLM_GGUF_DIR,
    DEFAULT_CHAT_MODEL,
    PROMPT_DIR,
    DEFAULT_PROMPT_NAME,
    N_GPU_LAYERS,
    LLAMA_CPP_VERBOSE
)
from app.services.llms.llama_cpp import LlamaCppLLM
from app.services.llms.base import BaseLLM


class LLMUnavailableError(RuntimeError):
    """模型目录为空 / 加载失败 —— 上层映射为 HTTP 503，而不是 500。"""


class LLMService:
    def __init__(self):
        self.models: Dict[str, Path] = {}
        self.active_model_name: str | None = None
        self.active_llm: BaseLLM | None = None
        self.load_error: str | None = None

        self.system_prompt = self._load_default_prompt()

        # 构造函数绝不能抛 —— 它是模块级单例，一抛就会让所有 import 了本模块的
        # 蓝图注册失败，整个 Flask 应用起不来。
        try:
            self.scan_models()
        except Exception as e:
            self.load_error = str(e)
            print(f"[LLM] 扫描模型失败（服务仍会启动，聊天接口返回 503）: {e}")
            return
        try:
            self.select_model(DEFAULT_CHAT_MODEL)
        except Exception as e:
            self.load_error = str(e)
            print(f"[LLM] 预加载模型失败（服务仍会启动，聊天接口返回 503）: {e}")

    # -------------------------------------------------
    # Prompt 管理
    # -------------------------------------------------
    def _load_default_prompt(self) -> str:
        default_file = PROMPT_DIR / f"{DEFAULT_PROMPT_NAME}.txt"
        if default_file.exists():
            return default_file.read_text(encoding="utf-8").strip()
        return ""

    def _load_prompt(self, prompt_name: str) -> str:
        prompt_file = PROMPT_DIR / f"{prompt_name}.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8").strip()
        return self.system_prompt

    # -------------------------------------------------
    # 模型扫描（只扫描生成模型 GGUF，过滤 embedding）
    # -------------------------------------------------
    def scan_models(self):
        if not LLM_GGUF_DIR.exists():
            raise RuntimeError(f"生成模型目录不存在: {LLM_GGUF_DIR}")

        print(f"[LLM] 扫描生成模型目录: {LLM_GGUF_DIR}")

        embedding_keywords = ["embed", "bge", "gte", "e5", "text-embedding"]

        for file in LLM_GGUF_DIR.iterdir():
            if file.suffix.lower() != ".gguf":
                continue

            name_lower = file.stem.lower()
            if any(kw in name_lower for kw in embedding_keywords):
                print(f"[LLM] 跳过 embedding GGUF: {file.name}")
                continue

            print(f"[LLM] 发现生成模型: {file.name}")
            self.models[file.stem] = file

        if not self.models:
            raise RuntimeError("未发现任何有效的生成 GGUF 模型")
        print(f"[LLM] 扫描到的生成模型: {list(self.models.keys())}")

    # -------------------------------------------------
    # 模型选择（加类型检查 + fallback）
    # -------------------------------------------------
    def select_model(self, model_name: str | None = None):
        # 前端不带具体模型名时传 "default"，它不是 self.models 的 key。
        # 早退条件要把它归一化，否则每次提问都会重走 fallback 重新加载
        # 7B 权重，首个 token 被推迟 5~9 秒。
        if model_name in (None, "", "default"):
            model_name = self.active_model_name
        else:
            model_name = model_name.strip()

        if model_name == self.active_model_name and self.active_llm is not None:
            return

        if not model_name or model_name not in self.models:
            # 默认选第一个
            if not self.models:
                raise LLMUnavailableError("没有可用生成模型")
            model_name = next(iter(self.models.keys()))
            print(f"[LLM] DEFAULT_CHAT_MODEL 无效，使用第一个模型: {model_name}")

        path = self.models[model_name]

        try:
            candidate = LlamaCppLLM(path)
        except Exception as e:
            candidate = None
            print(f"[LLM] 加载模型异常 {model_name}: {str(e)}")

        if candidate is not None and candidate.available:
            self.active_llm = candidate
            self.active_model_name = model_name
            self.load_error = None
            print(f"[LLM] 成功切换到模型: {model_name}")
            return

        # 首选模型没加载出来 → 依次试其余模型；全失败则保留扫描结果但标记不可用
        detail = (candidate.load_error if candidate else "") or "unknown"
        for fallback_name, fallback_path in self.models.items():
            if fallback_name == model_name:
                continue
            print(f"[LLM] fallback 到 {fallback_name}")
            try:
                fb = LlamaCppLLM(fallback_path)
            except Exception as e:
                print(f"[LLM] fallback {fallback_name} 也失败: {e}")
                continue
            if fb.available:
                self.active_llm = fb
                self.active_model_name = fallback_name
                self.load_error = None
                return
            detail = fb.load_error or detail

        self.active_llm = None
        self.active_model_name = None
        self.load_error = detail
        print(f"[LLM] 没有可用模型，聊天接口将返回 503。原因: {detail}")

    # -------------------------------------------------
    # 状态
    # -------------------------------------------------
    @property
    def available(self) -> bool:
        return self.active_llm is not None

    def status(self) -> dict:
        return {
            "available": self.available,
            "active_model": self.active_model_name,
            "discovered_models": list(self.models.keys()),
            "loaded_params": getattr(self.active_llm, "loaded_params", None),
            "error": self.load_error,
        }

    def ensure_available(self) -> None:
        """供上层在真正需要生成前调用；未加载时做一次重试。"""
        if self.active_llm is not None:
            return
        if not self.models:
            try:
                self.scan_models()
            except Exception as e:
                self.load_error = str(e)
        if self.models:
            try:
                self.select_model(DEFAULT_CHAT_MODEL)
            except Exception as e:
                self.load_error = str(e)
        if self.active_llm is None:
            raise LLMUnavailableError(
                f"生成模型不可用（{self.load_error or '未知原因'}）。"
                "请检查 models/llm/*.gguf 是否存在，以及显存/内存是否足够。"
            )

    # -------------------------------------------------
    # Token 统计（加防护）
    # -------------------------------------------------
    def _count_tokens(self, text: str) -> int:
        if not text or not self.active_llm or not hasattr(self.active_llm, 'llm'):
            return 0
        try:
            return len(self.active_llm.llm.tokenize(text.encode("utf-8")))
        except:
            return 0

    # -------------------------------------------------
    # Prompt 构造（支持 RAG）
    # -------------------------------------------------
    def _build_prompt_text_with_rag(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        rag_context: str | None = None,
    ) -> str:
        parts = []

        if system_prompt:
            parts.append(f"System: {system_prompt}")

        if rag_context:
            parts.append("Knowledge:")
            parts.append(rag_context)

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")

        parts.append("Assistant:")
        return "\n".join(parts)

    # -------------------------------------------------
    # OpenAI-compatible Chat Completions（加完整异常捕获）
    # -------------------------------------------------
    def chat_completions(
            self,
            messages: List[Dict[str, str]],
            stream: bool = False,
            model: str | None = None,
            prompt_name: str = DEFAULT_PROMPT_NAME,
            rag_context: str | None = None,
            **kwargs
    ):
        """
        OpenAI-compatible Chat Completions 接口
        支持：
        - 流式 / 非流式
        - RAG 上下文注入（作为 system 消息插入）
        - usage 统计
        - 详细异常捕获与日志
        """
        if model:
            self.select_model(model)

        self.ensure_available()
        if not self.active_llm or not hasattr(self.active_llm, 'llm'):
            raise LLMUnavailableError("没有加载任何生成模型，请检查模型目录")

        # 加载 prompt（作为 system message）
        system_prompt = self._load_prompt(prompt_name)

        # 构造 messages（插入 RAG 上下文作为额外 system 消息）
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})

        if rag_context and rag_context.strip():
            final_messages.append({"role": "system", "content": f"Knowledge Base Context:\n{rag_context}"})

        # 添加用户历史消息
        final_messages.extend(messages)

        # 计算 prompt tokens（使用模型 tokenizer）
        prompt_tokens = self._count_tokens(
            "\n".join([f"{m['role']}: {m['content']}" for m in final_messages])
        )

        try:
            # ================================
            # 非流式分支
            # ================================
            if not stream:
                output = self.active_llm.llm.create_chat_completion(
                    messages=final_messages,
                    max_tokens=kwargs.get("max_tokens", 512),
                    temperature=kwargs.get("temperature", 0.7),
                    top_p=kwargs.get("top_p", 0.9),
                    stop=kwargs.get("stop", ["</s>"]),
                    # echo=False,   ← 删除这一行！当前版本不支持
                )

                # 兼容不同版本的输出结构
                choice = output["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"].strip()
                elif "text" in choice:
                    content = choice["text"].strip()
                else:
                    content = ""
                    print("[WARNING] 未找到 content 或 text 字段，输出为空")

                if not content:
                    content = "（模型未生成有效回复，请检查 prompt 或模型配置）"

                completion_tokens = self._count_tokens(content)

                return {
                    "id": f"chatcmpl-{id(self)}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": self.active_model_name,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": output.get("choices", [{}])[0].get("finish_reason", "stop"),
                    }],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    }
                }

            # ================================
            # 流式分支
            # ================================
            else:
                def stream_generator():
                    completion_tokens = 0
                    collected_content = ""

                    for chunk in self.active_llm.llm.create_chat_completion(
                            messages=final_messages,
                            max_tokens=kwargs.get("max_tokens", 512),
                            temperature=kwargs.get("temperature", 0.7),
                            top_p=kwargs.get("top_p", 0.9),
                            stream=True,
                            # echo=False,   ← 流式也删除
                    ):
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            delta_content = delta["content"]
                            collected_content += delta_content
                            completion_tokens += self._count_tokens(delta_content)

                            yield {
                                "id": f"chatcmpl-{id(self)}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": self.active_model_name,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"role": "assistant", "content": delta_content},
                                    "finish_reason": None
                                }],
                                "usage": None
                            }

                    # 结束 chunk
                    yield {
                        "id": f"chatcmpl-{id(self)}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": self.active_model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens,
                        }
                    }

                return stream_generator()

        except Exception as e:
            import traceback
            error_detail = f"[chat_completions 异常] {str(e)}\n{traceback.format_exc()}"
            print(error_detail)
            raise RuntimeError(error_detail)


# 全局单例
llm_service = LLMService()