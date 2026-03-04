# app/services/embedding_factory.py
"""
Embedding 模型的工厂模块：负责扫描、缓存、实例化 EmbeddingService
这个文件**不应该**导入任何 rag、kb、retriever 相关模块，避免循环导入
"""

import os
import sys
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union

from sentence_transformers import SentenceTransformer
from app.config.settings import PROJECT_ROOT

# 新增配置导入（如果 settings 中不存在这些配置，需要添加）
try:
    from app.config.settings import (
        EMBEDDING_SCAN_PATH,
        EMBEDDING_GGUF_SCAN_PATH,
        DEFAULT_EMBEDDING_MODEL,
        N_GPU_LAYERS,
        LLAMA_CPP_VERBOSE
    )
except ImportError:
    # 如果 settings 中没有这些配置，使用默认值
    EMBEDDING_SCAN_PATH = str(PROJECT_ROOT / "models" / "embedding")
    EMBEDDING_GGUF_SCAN_PATH = str(PROJECT_ROOT / "models" / "embedding" / "gguf")
    DEFAULT_EMBEDDING_MODEL = "bge-small-zh-v1.5"
    N_GPU_LAYERS = 0
    LLAMA_CPP_VERBOSE = False

try:
    from llama_cpp import Llama  # 用于 GGUF embedding

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None

logger = logging.getLogger(__name__)

# 全局缓存（模块级别）
_model_cache: Dict[str, Union['SimpleEmbeddingService', 'SentenceEmbedding', 'LlamaCppEmbedding']] = {}
_model_path_cache: Dict[str, str] = {}
_model_dim_cache: Dict[str, int] = {}
_model_type_cache: Dict[str, str] = {}  # 'hf' 或 'gguf'

# 保持向后兼容的默认模型配置
DEFAULT_MODEL_NAME = DEFAULT_EMBEDDING_MODEL if 'DEFAULT_EMBEDDING_MODEL' in dir() else "bge-small-zh-v1.5"
DEFAULT_MODEL_PATH = str(PROJECT_ROOT / "models" / "embedding" / DEFAULT_MODEL_NAME)


def scan_embedding_models(embedding_root: str | Path = None) -> Dict[str, str]:
    """
    扫描本地 embedding 模型目录，支持 HuggingFace 格式和 GGUF 格式
    返回 {模型名: 绝对路径}
    """
    global _model_path_cache, _model_dim_cache, _model_type_cache

    # 保持向后兼容：如果传入 embedding_root，优先使用
    if embedding_root is not None:
        embedding_root = Path(embedding_root).resolve()
        if not embedding_root.is_dir():
            logger.warning(f"embedding 根目录不存在: {embedding_root}")
            return {}

        # 使用传统方式扫描（保持原有逻辑）
        new_cache = {}
        new_dim_cache = {}

        for subdir in embedding_root.iterdir():
            if not subdir.is_dir():
                continue
            model_name = subdir.name.strip()
            if not model_name:
                continue

            config_path = subdir / "config.json"
            has_weight = any(
                (subdir / f).exists()
                for f in ["pytorch_model.bin", "model.safetensors", "adapter_model.safetensors"]
            )

            if config_path.exists() and has_weight:
                abs_path = str(subdir.resolve())
                new_cache[model_name] = abs_path
                _model_type_cache[model_name] = "hf"

                # 尝试预读维度（更鲁棒一些）
                try:
                    import json
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    # 常见字段：hidden_size / dim / embedding_dim
                    dim = (
                            config.get("hidden_size")
                            or config.get("dim")
                            or config.get("embedding_dim")
                            or config.get("intermediate_size")  # 少数模型用这个
                    )
                    if dim:
                        new_dim_cache[model_name] = int(dim)
                except Exception as e:
                    logger.debug(f"无法预读 dim ({model_name}): {e}")

        if new_cache:
            _model_path_cache.update(new_cache)
            _model_dim_cache.update(new_dim_cache)
            logger.info(f"扫描到 {len(new_cache)} 个有效 embedding 模型: {list(new_cache.keys())}")
        else:
            logger.warning("未扫描到任何有效 embedding 模型")

        return new_cache

    # 新逻辑：扫描两种格式的 embedding 模型
    # 1. 扫描 HuggingFace 文件夹
    hf_root = Path(EMBEDDING_SCAN_PATH)
    if hf_root.exists():
        for subdir in hf_root.iterdir():
            if not subdir.is_dir():
                continue
            name = subdir.name.strip()
            if name and (subdir / "config.json").exists():
                abs_path = str(subdir.resolve())
                _model_path_cache[name] = abs_path
                _model_type_cache[name] = "hf"

                # 保持原有逻辑：尝试预读维度
                try:
                    import json
                    config_path = subdir / "config.json"
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    dim = (
                            config.get("hidden_size")
                            or config.get("dim")
                            or config.get("embedding_dim")
                            or config.get("intermediate_size")
                    )
                    if dim:
                        _model_dim_cache[name] = int(dim)
                except Exception as e:
                    logger.debug(f"无法预读 dim ({name}): {e}")

                logger.info(f"发现 HF embedding 模型: {name}")

    # 2. 扫描 GGUF embedding 文件
    if LLAMA_CPP_AVAILABLE:
        gguf_root = Path(EMBEDDING_GGUF_SCAN_PATH)
        if gguf_root.exists():
            for file in gguf_root.glob("*.gguf"):
                name = file.stem
                abs_path = str(file.resolve())
                _model_path_cache[name] = abs_path
                _model_type_cache[name] = "gguf"

                # 尝试从 GGUF 文件获取维度（需要加载模型）
                # 这里先不预读，避免启动时加载过慢
                logger.info(f"发现 GGUF embedding 模型: {name}")

    if not _model_path_cache:
        logger.warning("未发现任何 embedding 模型（HF 或 GGUF）")

    return _model_path_cache.copy()


def get_available_embedding_models() -> List[Dict[str, any]]:
    """返回可用的 embedding 模型列表（供 API 使用）"""
    models = []
    for name, path in _model_path_cache.items():
        dim = _model_dim_cache.get(name)
        model_type = _model_type_cache.get(name, "hf")
        models.append(
            {
                "name": name,
                "path": path,
                "dim": dim if dim is not None else "未知",
                "type": model_type,
                "is_default": name == DEFAULT_MODEL_NAME,
            }
        )
    return models


# 保持原有类不变（向后兼容）
class SimpleEmbeddingService:
    """轻量包装 sentence-transformers，提供统一接口"""
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(5000)  # 先拉高到 5000 测试
    logger.info("递归上限临时设置为 5000 (原: %d)", old_limit)

    def __init__(self, model_name_or_path: str, device: str = None):
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np

            self.model = SentenceTransformer(
                model_name_or_path,
                device=device or "cpu",
                trust_remote_code=True,
            )
            self.dim = self.model.get_sentence_embedding_dimension() or 384
        except RecursionError as re:
            import traceback
            logger.critical("RecursionError 发生！堆栈：\n" + traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"加载失败: {model_name_or_path}", exc_info=True)
            raise

    def embed(self, texts: List[str]) -> 'np.ndarray':
        """批量 embedding，返回 numpy array"""
        if not texts:
            return np.array([])

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,  # 强制返回 numpy
        )
        logger.debug(f"Embedding 返回类型: {type(embeddings)}, shape: {getattr(embeddings, 'shape', 'N/A')}")
        # 在 SimpleEmbeddingService.__init__ 最后
        logger.info(f"模型加载完成，维度: {self.dim}, 示例输入测试: {self.embed(['测试'])[0][:8]}...")

        return embeddings  # 直接返回 np.ndarray，不转 list


# 新增 HuggingFace 加载类（基于 sentence-transformers，支持 CUDA）
class SentenceEmbedding:
    def __init__(self, path: str):
        import torch
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            path,
            device="cuda" if torch.cuda.is_available() else "cpu",
            trust_remote_code=True
        )
        self.dim = self.model.get_sentence_embedding_dimension() or 384

    def embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=32,
            show_progress_bar=False
        )


# 新增 GGUF embedding 加载类（llama.cpp）
class LlamaCppEmbedding:
    def __init__(self, path: str):
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp-python 未安装，无法加载 GGUF 模型")

        self.llm = Llama(
            model_path=path,
            embedding=True,  # 关键：embedding 模式
            n_gpu_layers=N_GPU_LAYERS,
            verbose=LLAMA_CPP_VERBOSE,
            n_ctx=8192,  # embedding 不需要太长上下文
        )
        # 从 metadata 尝试获取 dim（或硬编码常见值）
        self.dim = self.llm.metadata.get("embedding_length", 384)

    def embed(self, texts: List[str]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return np.array([])

        embeddings = []
        for text in texts:
            emb = self.llm.embed(text)
            embeddings.append(emb)
        return np.array(embeddings, dtype=np.float32)


def get_embedding_service(model_name: str = None):
    """
    获取 embedding 服务，支持 HuggingFace 格式和 GGUF 格式
    保持向后兼容：如果新逻辑失败，回退到原有在线加载逻辑
    """
    if not model_name:
        model_name = DEFAULT_EMBEDDING_MODEL

    # 检查缓存
    if model_name in _model_cache:
        return _model_cache[model_name]

    path = _model_path_cache.get(model_name)

    # 如果本地没有找到，尝试 fallback 到默认模型
    if not path:
        logger.warning(f"未找到 embedding 模型 {model_name}，尝试 fallback 到默认模型")
        model_name = DEFAULT_EMBEDDING_MODEL
        path = _model_path_cache.get(model_name)

    # 如果本地有路径，根据类型加载
    if path:
        model_type = _model_type_cache.get(model_name, "hf")

        try:
            if model_type == "hf":
                svc = SentenceEmbedding(path)
            elif model_type == "gguf":
                svc = LlamaCppEmbedding(path)
            else:
                # 未知类型，尝试用 SimpleEmbeddingService 兼容加载
                svc = SimpleEmbeddingService(path)

            _model_cache[model_name] = svc
            logger.info(f"加载 embedding 成功: {model_name} ({model_type}), dim={svc.dim}")
            return svc

        except Exception as e:
            logger.error(f"加载 {model_name} 失败: {str(e)}", exc_info=True)
            # 如果本地加载失败，继续尝试在线 fallback（保持原有逻辑）
            logger.info("本地加载失败，尝试在线 fallback")

    # 保持原有逻辑：fallback 到在线 huggingface 模型
    logger.info(f"【测试】强制使用在线 BAAI/bge-small-zh-v1.5，跳过本地加载")
    try:
        svc = SimpleEmbeddingService("BAAI/bge-small-zh-v1.5")
        logger.info("在线模型加载成功，dim = %s", svc.dim)
        # 缓存在线模型
        _model_cache[model_name] = svc
        return svc
    except Exception as e:
        logger.critical("在线加载也失败: %s", str(e), exc_info=True)
        raise RuntimeError(
            f"无法加载 embedding 模型 {model_name}，请检查本地路径或网络连接"
        )