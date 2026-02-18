# app/rag/embedding.py
from sentence_transformers import SentenceTransformer
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    支持本地路径或 huggingface id 的 embedding 服务（优先本地）
    """
    def __init__(self, model_name_or_path: str = None, default_model="BAAI/bge-small-zh-v1.5"):
        """
        model_name_or_path: 本地绝对路径 或 huggingface 模型名
        """
        if model_name_or_path and os.path.isdir(model_name_or_path):
            logger.info(f"加载本地模型: {model_name_or_path}")
            self.model = SentenceTransformer(model_name_or_path)
        else:
            # fallback 到在线模型（仅当本地路径无效时）
            logger.info(f"加载在线模型 (fallback): {default_model}")
            self.model = SentenceTransformer(default_model)

        dim = self.model.get_sentence_embedding_dimension()
        if dim is None:
            raise RuntimeError("无法获取模型维度")

        self.dim = int(dim)
        logger.info(f"EmbeddingService 初始化完成，维度: {self.dim}")

    def embed(self, texts):
        """
        输入：list[str] 或 str
        输出：np.ndarray (n, dim)，已归一化
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=32,                  # 批量优化
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 50,  # 大批量才显示进度
                convert_to_numpy=True
            )
            return embeddings.astype("float32")
        except Exception as e:
            logger.error(f"embedding 失败: {str(e)}")
            raise