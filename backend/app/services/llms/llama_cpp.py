# app/services/llms/llama_cpp.py
from pathlib import Path
from llama_cpp import Llama

from app.services.llms.base import BaseLLM


class LlamaCppLLM(BaseLLM):
    def __init__(self, model_path: Path):
        super().__init__(model_path)
        self.llm = None
        self.load()

    def load(self):
        print(f"[LLM] 加载模型: {self.model_path}")

        self.llm = Llama(
            model_path=str(self.model_path),
            n_ctx=4096,
            n_threads=8,
        )

    def chat(self, message: str) -> str:
        output = self.llm(
            message,
            max_tokens=512,
            stop=["</s>"],
        )

        return output["choices"][0]["text"].strip()
