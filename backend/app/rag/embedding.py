# app/rag/embedding.py
import numpy as np


class EmbeddingService:
    """
    简单 embedding 服务（先用随机向量占位）
    后期替换成真实 embedding 模型
    """

    def __init__(self, dim=768):
        self.dim = dim

    def embed(self, texts):
        """
        输入：
            texts: list[str]
        输出：
            np.ndarray shape = (n, dim)
        """
        return np.random.rand(len(texts), self.dim).astype("float32")
