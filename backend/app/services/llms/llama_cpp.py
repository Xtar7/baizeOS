# backend/app/services/llms/llama_cpp.py
"""llama.cpp 后端封装。

关键设计：load() 永不向上抛异常。
显存 / 内存不足时 llama.cpp 只会抛 "Failed to create llama_context"，
早期版本把它透传成模块级 ImportError，会让整个 Flask 应用起不来
（所有 import 了 llm_service 的蓝图被 register_blueprints 静默跳过，
前端于是表现为"连不上后端"）。这里改为按阶梯降级重试，全失败才记录
错误并置空，由上层在真正需要生成时给出 503。
"""
import logging
import time
from pathlib import Path
from typing import Dict, Generator, List, Union

from llama_cpp import Llama

from app.config.settings import (
    LLM_LOAD_LADDER,
    LLM_N_BATCH,
    LLM_N_CTX,
    LLM_N_GPU_LAYERS,
    LLM_N_THREADS,
    LLAMA_CPP_VERBOSE,
)
from app.services.llms.base import BaseLLM
from app.services.llms.gpu_probe import safe_gpu_layers

logger = logging.getLogger(__name__)


class LlamaCppLLM(BaseLLM):
    def __init__(self, model_path: Path):
        super().__init__(model_path)
        self.llm = None
        self.load_error: str | None = None
        self.loaded_params: Dict[str, int] | None = None
        self.load()

    # ----------------------------
    # 模型加载（带降级阶梯，失败不抛）
    # ----------------------------
    def load(self) -> bool:
        print(f"[LLM] 加载生成模型: {self.model_path}")

        try:
            model_size = self.model_path.stat().st_size
        except OSError:
            model_size = 0

        ladder: List[Dict[str, int]] = list(LLM_LOAD_LADDER) or [
            {"n_ctx": LLM_N_CTX, "n_gpu_layers": LLM_N_GPU_LAYERS}
        ]
        last_error = ""

        for params in ladder:
            n_ctx = params.get("n_ctx", LLM_N_CTX)
            requested_gpu = params.get("n_gpu_layers", LLM_N_GPU_LAYERS)
            # 显存装不下时 llama.cpp 会 GGML_ASSERT 直接 abort 进程，
            # 必须在尝试之前按空闲显存把 offload 层数收敛到安全值。
            n_gpu_layers = (
                safe_gpu_layers(model_size, n_ctx, requested_gpu)
                if model_size
                else requested_gpu
            )
            attempt = {
                "n_ctx": n_ctx,
                "n_gpu_layers": n_gpu_layers,
                "n_threads": LLM_N_THREADS,
                "n_batch": LLM_N_BATCH,
            }
            started = time.time()
            try:
                self.llm = Llama(
                    model_path=str(self.model_path),
                    verbose=LLAMA_CPP_VERBOSE,  # 生产关闭，调试可临时打开
                    **attempt,
                )
            except Exception as e:  # 显存/内存不足 → 换下一档
                last_error = f"{type(e).__name__}: {e}"
                self.llm = None
                print(
                    f"[LLM] 加载失败(n_ctx={attempt['n_ctx']}, "
                    f"n_gpu_layers={attempt['n_gpu_layers']}) → {last_error}，尝试降级 …"
                )
                continue

            self.loaded_params = attempt
            self.load_error = None
            print(
                f"[LLM] 模型加载成功: {self.model_name} "
                f"(n_ctx={attempt['n_ctx']}, n_gpu_layers={attempt['n_gpu_layers']}, "
                f"{time.time() - started:.1f}s)"
            )
            return True

        self.load_error = last_error or "unknown"
        print(f"[LLM] 全部加载档位均失败: {self.model_path} → {self.load_error}")
        return False

    @property
    def available(self) -> bool:
        return self.llm is not None

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
        if self.llm is None:
            raise RuntimeError(f"模型未加载: {self.load_error}")
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
        if self.llm is None:
            raise RuntimeError(f"模型未加载: {self.load_error}")
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
