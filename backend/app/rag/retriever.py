from app.rag.embedding import EmbeddingService
from app.rag.index_manager import IndexManager


class Retriever:
    def __init__(self, dim=768):
        self.embedding = EmbeddingService(dim)
        self.index_manager = IndexManager(dim)

    def add_documents(self, texts, kb_id="default"):
        vectors = self.embedding.embed(texts)
        self.index_manager.add(vectors, texts, kb_id)
        self.index_manager.save(kb_id)

    def search(self, query, kb_id="default", top_k=5):
        query_vec = self.embedding.embed([query])
        return self.index_manager.search(query_vec, kb_id, top_k)


# 全局实例
retriever = Retriever()