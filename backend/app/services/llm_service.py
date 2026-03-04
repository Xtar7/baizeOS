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


class LLMService:
    def __init__(self):
        print("!!! 使用的是 2025-03-最新版 llm_service.py (有 embedding 过滤) !!!")
        self.models: Dict[str, Path] = {}
        self.active_model_name: str | None = None
        self.active_llm: BaseLLM | None = None

        self.system_prompt = self._load_default_prompt()

        self.scan_models()
        self.select_model(DEFAULT_CHAT_MODEL)

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
        print("[DEBUG] 扫描到的生成模型列表:", list(self.models.keys()))
        if self.models:
            print("[DEBUG] 默认加载模型:", next(iter(self.models.keys())))
        else:
            print("[DEBUG] 没有找到任何生成模型！！！")

    # -------------------------------------------------
    # 模型选择（加类型检查 + fallback）
    # -------------------------------------------------
    def select_model(self, model_name: str | None = None):
        if model_name == self.active_model_name and self.active_llm:
            return

        if not model_name or model_name not in self.models:
            # 默认选第一个
            if not self.models:
                raise RuntimeError("没有可用生成模型")
            model_name = next(iter(self.models.keys()))
            print(f"[LLM] DEFAULT_CHAT_MODEL 无效，使用第一个模型: {model_name}")

        path = self.models[model_name]

        try:
            self.active_llm = LlamaCppLLM(path)
            self.active_model_name = model_name
            print(f"[LLM] 成功切换到模型: {model_name}")
        except Exception as e:
            print(f"[LLM] 加载模型失败 {model_name}: {str(e)}")
            # fallback 到第一个可用
            fallback_name = next(iter(self.models.keys()))
            if fallback_name != model_name:
                print(f"[LLM] fallback 到 {fallback_name}")
                self.active_llm = LlamaCppLLM(self.models[fallback_name])
                self.active_model_name = fallback_name
            else:
                raise
            print("[DEBUG] 当前 active_model_name:", self.active_model_name)
            print("[DEBUG] 当前模型路径:", self.active_llm.model_path if self.active_llm else "None")

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

        if not self.active_llm or not hasattr(self.active_llm, 'llm'):
            raise RuntimeError("没有加载任何生成模型，请检查模型目录")

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

                # 调试打印（上线可注释）
                print("[DEBUG] 非流式 output 结构:", output)

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