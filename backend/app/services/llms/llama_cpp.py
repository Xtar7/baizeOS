# backend/app/services/llms/llama_cpp.py
from pathlib import Path
from typing import List, Dict, Generator, Union
from llama_cpp import Llama

from app.config.settings import N_GPU_LAYERS, LLAMA_CPP_VERBOSE
from app.services.llms.base import BaseLLM


class LlamaCppLLM(BaseLLM):
    def __init__(self, model_path: Path):
        super().__init__(model_path)
        self.llm = None
        self.load()

    def load(self):
        print(f"[LLM] 加载生成模型: {self.model_path}")

        try:
            self.llm = Llama(
                model_path=str(self.model_path),
                n_ctx=8192,
                n_gpu_layers=N_GPU_LAYERS,      # 支持 GPU 全 offload
                n_threads=8,
                n_batch=512,
                verbose=LLAMA_CPP_VERBOSE,      # 生产关闭，调试可临时打开
            )
            print(f"[LLM] 模型加载成功: {self.model_name}")
        except Exception as e:
            print(f"[LLM] 加载失败: {self.model_path} → {str(e)}")
            raise

    # ----------------------------
    # prompt 构造（保持原有）
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
    # 对话接口（加异常捕获）
    # ----------------------------
    def chat(self, messages: List[Dict]) -> str:
        try:
            output = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=512,
                temperature=0.7,
            )
            return output["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM chat] 生成失败: {str(e)}")
            raise

    def stream_chat(self, messages: List[Dict]) -> Generator[str, None, None]:
        try:
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
        except Exception as e:
            print(f"[LLM stream_chat] 流式生成失败: {str(e)}")
            raise