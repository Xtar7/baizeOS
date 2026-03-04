# backend/app/services/llm_service.py
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
        if model:
            self.select_model(model)

        system_prompt = self._load_prompt(prompt_name)

        prompt_text = self._build_prompt_text_with_rag(
            system_prompt,
            messages,
            rag_context,
        )

        prompt_tokens = self._count_tokens(prompt_text)

        try:
            if not stream:
                output = self.active_llm.llm(
                    prompt_text,
                    max_tokens=512,
                    stop=["</s>"],
                    echo=False,
                )

                content = output["choices"][0]["text"].strip()
                completion_tokens = self._count_tokens(content)

                return {
                    "content": content,
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    },
                    "model": self.active_model_name,
                }

            else:
                def stream_generator():
                    completion_tokens = 0
                    for chunk in self.active_llm.llm(
                        prompt_text,
                        max_tokens=512,
                        stream=True,
                    ):
                        delta = chunk["choices"][0]["text"]
                        completion_tokens += self._count_tokens(delta)
                        yield {
                            "delta": delta,
                        }

                    yield {
                        "done": True,
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens,
                        },
                        "model": self.active_model_name,
                    }

                return stream_generator()

        except Exception as e:
            import traceback
            error_msg = f"[chat_completions] 严重错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise RuntimeError(error_msg)


# 全局单例
llm_service = LLMService()