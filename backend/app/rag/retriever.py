# app/rag/retriever.py
from app.rag.embedding import EmbeddingService
from app.rag.index_manager import IndexManager
from app.services.kb_service import kb_service
from app.services.embedding_factory import get_embedding_service
import logging

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self):
        self.embedding = None
        self.index_managers = {}

    def _get_embedding(self, kb_id: str):
        if self.embedding is None:
            # 这里才导入（延迟到真正需要时）
            from app.services.embedding_factory import get_embedding_service

            meta = kb_service.get(kb_id)   # kb_service 也建议延迟，如果它也参与循环
            if not meta:
                raise ValueError(f"知识库 {kb_id} 不存在")
            model_name = meta.get("embedding_model", "bge-small-zh-v1.5")
            self.embedding = get_embedding_service(model_name)
        return self.embedding

    def _get_index_manager(self, kb_id: str) -> IndexManager:
        if kb_id not in self.index_managers:
            meta = kb_service.get(kb_id)
            dim = meta.get("embedding_dim", 512) if meta else 512
            self.index_managers[kb_id] = IndexManager(dim=dim)
        return self.index_managers[kb_id]

    def add_documents(self, texts, kb_id="default"):
        embedding = self._get_embedding(kb_id)
        vectors = embedding.embed(texts)
        index_manager = self._get_index_manager(kb_id)
        index_manager.add(vectors, texts, kb_id)
        index_manager.save(kb_id)

    def search(self, query, kb_id="default", top_k=5):
        embedding = self._get_embedding(kb_id)
        query_vec = embedding.embed([query])
        index_manager = self._get_index_manager(kb_id)
        return index_manager.search(query_vec, kb_id, top_k)

# 全局实例（可选保留）
retriever = Retriever()