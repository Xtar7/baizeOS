from pathlib import Path
from typing import List, Dict, Generator, Union
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

    # ----------------------------
    # prompt 构造
    # ----------------------------
    def build_prompt(self, messages: List[Dict], system_prompt: str) -> str:
        prompt = f"System: {system_prompt}\n"

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"

        prompt += "Assistant:"
        return prompt

    # ----------------------------
    # 对话接口
    # ----------------------------
    def chat(self, messages):
        output = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )

        return output["choices"][0]["message"]["content"]

    def stream_chat(self, messages):
        stream = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=512,
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            if "content" in delta:
                yield delta["content"]
