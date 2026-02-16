# backend/app/services/llm_service.py
from pathlib import Path
from typing import List, Dict, Any, Generator
from app.config.settings import LLM_SCAN_PATH, DEFAULT_CHAT_MODEL
from app.services.llms.llama_cpp import LlamaCppLLM


# ================================
# 路径配置
# ================================
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROMPT_DIR = PROJECT_ROOT / "config" / "prompts"
DEFAULT_PROMPT_FILE = PROMPT_DIR / "default.txt"


class LLMService:
    def __init__(self):
        self.models: Dict[str, Path] = {}
        self.active_model_name: str | None = None
        self.active_llm: LlamaCppLLM | None = None

        self.system_prompt = self._load_default_prompt()

        self.scan_models()
        self.select_model(DEFAULT_CHAT_MODEL)

    # -------------------------------------------------
    # Prompt 管理
    # -------------------------------------------------
    def _load_default_prompt(self) -> str:
        if DEFAULT_PROMPT_FILE.exists():
            return DEFAULT_PROMPT_FILE.read_text(encoding="utf-8").strip()
        return ""

    def _load_prompt(self, prompt_name: str) -> str:
        """
        加载指定 prompt
        """
        prompt_file = PROMPT_DIR / f"{prompt_name}.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8").strip()
        return self.system_prompt

    # -------------------------------------------------
    # 模型管理
    # -------------------------------------------------
    def scan_models(self):
        if not LLM_SCAN_PATH.exists():
            raise RuntimeError(f"模型目录不存在: {LLM_SCAN_PATH}")

        print(f"[LLM] 扫描模型目录: {LLM_SCAN_PATH}")

        for file in LLM_SCAN_PATH.iterdir():
            if file.suffix.lower() == ".gguf":
                print(f"[LLM] 发现模型: {file.name}")
                self.models[file.stem] = file

        if not self.models:
            raise RuntimeError("未发现任何 GGUF 模型")

    def select_model(self, model_name: str | None = None):
        """
        模型选择（带热切换优化）
        """
        # 如果模型没变，不重复加载
        if model_name == self.active_model_name and self.active_llm:
            return

        if model_name and model_name in self.models:
            path = self.models[model_name]
        else:
            # 默认选择第一个
            path = next(iter(self.models.values()))
            model_name = path.stem

        print(f"[LLM] 使用模型: {model_name}")

        self.active_llm = LlamaCppLLM(path)
        self.active_model_name = model_name

    # -------------------------------------------------
    # Token 统计
    # -------------------------------------------------
    def _count_tokens(self, text: str) -> int:
        if not text or not self.active_llm:
            return 0
        llm = self.active_llm.llm
        return len(llm.tokenize(text.encode("utf-8")))

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

        # RAG 注入位置
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
    # OpenAI-compatible Chat Completions
    # -------------------------------------------------
    def chat_completions(
            self,
            messages: List[Dict[str, str]],
            stream: bool = False,  # 保持原位置
            model: str | None = None,
            prompt_name: str = "default",
            rag_context: str | None = None,
            **kwargs
    ):
        """
        OpenAI 风格对话入口
        支持：
        - 多模型切换
        - 多 prompt
        - RAG 上下文注入
        - usage 统计
        """

        if model:
            self.select_model(model)

        # 加载 prompt
        system_prompt = self._load_prompt(prompt_name)

        prompt_text = self._build_prompt_text_with_rag(
            system_prompt,
            messages,
            rag_context,
        )

        prompt_tokens = self._count_tokens(prompt_text)

        # ---------------- 非流式 ----------------
        if not stream:
            output = self.active_llm.llm(
                prompt_text,
                max_tokens=512,
                stop=["</s>"],
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

        # ---------------- 流式 ----------------
        def stream_generator() -> Generator[Dict[str, Any], None, None]:
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


# 全局单例
llm_service = LLMService()