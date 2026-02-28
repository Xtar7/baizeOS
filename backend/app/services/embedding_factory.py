# app/services/embedding_factory.py
"""
Embedding 模型的工厂模块：负责扫描、缓存、实例化 EmbeddingService
这个文件**不应该**导入任何 rag、kb、retriever 相关模块，避免循环导入
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 全局缓存（模块级别）
_model_path_cache: Dict[str, str] = {}
_model_dim_cache: Dict[str, int] = {}

DEFAULT_MODEL_NAME = "bge-small-zh-v1.5"
# 注意：这里使用你项目中真实的默认路径，建议从配置读取
DEFAULT_MODEL_PATH = r"\baizeOS\models\embedding\bge-small-zh-v1.5"  # 请替换成实际路径或从配置读取


def scan_embedding_models(embedding_root: str | Path) -> Dict[str, str]:
    """扫描本地 embedding 模型目录，返回 {模型名: 绝对路径}"""
    global _model_path_cache, _model_dim_cache

    embedding_root = Path(embedding_root).resolve()
    if not embedding_root.is_dir():
        logger.warning(f"embedding 根目录不存在: {embedding_root}")
        return {}

    new_cache = {}
    new_dim_cache = {}

    for subdir in embedding_root.iterdir():
        if not subdir.is_dir():
            continue
        model_name = subdir.name.strip()
        if not model_name:
            continue

        config_path = subdir / "config.json"
        has_weight = any((subdir / f).exists() for f in ["pytorch_model.bin", "model.safetensors"])

        if config_path.exists() and has_weight:
            abs_path = str(subdir.resolve())
            new_cache[model_name] = abs_path

            # 尝试预读维度
            try:
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                dim = config.get("hidden_size") or config.get("dim") or config.get("embedding_dim")
                if dim:
                    new_dim_cache[model_name] = int(dim)
            except Exception as e:
                logger.debug(f"无法预读 dim ({model_name}): {e}")

    if new_cache:
        _model_path_cache = new_cache
        _model_dim_cache = new_dim_cache
        logger.info(f"扫描到 {len(new_cache)} 个有效 embedding 模型: {list(new_cache.keys())}")
    else:
        logger.warning("未扫描到任何有效 embedding 模型")

    return new_cache


def get_available_embedding_models() -> List[Dict[str, any]]:
    """返回可用的 embedding 模型列表（供 API 使用）"""
    models = []
    for name, path in _model_path_cache.items():
        dim = _model_dim_cache.get(name)
        models.append({
            "name": name,
            "path": path,
            "dim": dim if dim is not None else "未知",
            "is_default": name == DEFAULT_MODEL_NAME
        })
    return models


def get_embedding_service(model_name: str = None) -> 'EmbeddingService':
    from app.rag.embedding import EmbeddingService   # ← 移到这里

    if not model_name:
        model_name = DEFAULT_MODEL_NAME

    path = _model_path_cache.get(model_name)

    if not path or not os.path.isdir(path):
        logger.warning(f"模型 {model_name} 路径无效，使用默认 {DEFAULT_MODEL_NAME}")
        path = DEFAULT_MODEL_PATH
        model_name = DEFAULT_MODEL_NAME

    try:
        svc = EmbeddingService(model_name_or_path=path)
        logger.debug(f"成功加载模型: {model_name} (dim={svc.dim})")
        return svc
    except Exception as e:
        logger.error(f"本地模型 {model_name} 加载失败: {str(e)}")
        try:
            svc = EmbeddingService(default_model="BAAI/bge-small-zh-v1.5")
            logger.info("fallback 到在线 bge-small-zh-v1.5 成功")
            return svc
        except Exception as online_err:
            logger.critical(f"在线模型也失败: {str(online_err)}")
            raise RuntimeError("所有 embedding 模型加载失败，请检查路径和网络")