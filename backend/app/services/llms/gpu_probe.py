# backend/app/services/llms/gpu_probe.py
"""显存探测 + 安全 offload 层数估算。

为什么需要它：llama.cpp 在显存不够时不会抛 Python 异常，而是触发 C 层
GGML_ASSERT 直接 abort 掉整个进程（连 try/except 都接不住）。所以"失败就
降级重试"的思路对 GPU offload 无效 —— 必须在尝试之前就判断装不装得下。

只依赖标准库 + nvidia-smi，探测不到就退化为 CPU（永远安全）。
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 消费级显卡上就算显存富余，全量 offload 也没有收益，且极易在长上下文时
# 因计算缓冲区爆掉。这里给一个上限。
MAX_OFFLOAD_LAYERS = 24
# 估算的安全系数：显存不是独占的，且还有计算缓冲区 / CUDA context 要留。
SAFETY_FACTOR = 0.80
# 假设的 transformer block 数。用于把"模型文件总大小"摊成"每层大小"。
# 取偏大的值会让每层估算偏小（更保守）；7B/8B 量级通常 32~43，取 33。
ASSUMED_BLOCKS = 33


def _query_nvidia_smi() -> Optional[Tuple[int, int]]:
    """返回 (total_mb, free_mb)；查询不到返回 None。"""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "--query-gpu=memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0:
            return None
        first = out.stdout.strip().splitlines()[0]
        total_s, free_s = re.split(r"[,\s]+", first.strip())[:2]
        return int(float(total_s)), int(float(free_s))
    except Exception as e:
        logger.debug(f"[gpu] nvidia-smi 查询失败: {e}")
        return None


def free_vram_mb() -> Optional[int]:
    probe = _query_nvidia_smi()
    return probe[1] if probe else None


def safe_gpu_layers(
    model_size_bytes: int,
    n_ctx: int,
    requested: int,
) -> int:
    """把"期望的 n_gpu_layers"收敛成一个不会把进程搞崩的数。

    requested <= 0 视为"全量 offload"，同样走估算。
    """
    if requested == 0:
        return 0

    probe = _query_nvidia_smi()
    if probe is None:
        logger.info("[gpu] 未探测到 NVIDIA 显卡，使用纯 CPU 推理")
        return 0
    total_mb, free_mb = probe

    budget_mb = free_mb * SAFETY_FACTOR
    if requested < 0:
        # 全量 offload：还要装 KV cache 和计算缓冲区
        # KV cache 粗估 56KB/token（Qwen2.5-7B GQA），计算缓冲区 ~400MB
        kv_mb = n_ctx * 56 / 1024
        weights_budget = budget_mb - kv_mb - 400
        if weights_budget <= 0:
            logger.info(
                f"[gpu] 空闲显存 {free_mb}MB 不足以承载 n_ctx={n_ctx} 的上下文，纯 CPU"
            )
            return 0
        per_layer_mb = model_size_bytes / (ASSUMED_BLOCKS * 1024 * 1024)
        layers = int(weights_budget / per_layer_mb)
    else:
        per_layer_mb = model_size_bytes / (ASSUMED_BLOCKS * 1024 * 1024)
        layers = int((budget_mb - 400) / per_layer_mb)

    layers = max(0, min(layers, MAX_OFFLOAD_LAYERS, requested if requested > 0 else MAX_OFFLOAD_LAYERS))

    if requested < 0 and layers >= MAX_OFFLOAD_LAYERS:
        logger.info(f"[gpu] 空闲显存 {free_mb}MB，可全量 offload")
    else:
        logger.info(
            f"[gpu] 空闲显存 {free_mb}MB/{total_mb}MB，每层约 {per_layer_mb:.0f}MB "
            f"→ n_gpu_layers={layers}（请求 {requested}）"
        )
    return layers
