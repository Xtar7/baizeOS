# app/services/embedding_service.py
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("BAAI/bge-small-zh")

    def embed(self, texts):
        return self.model.encode(texts).tolist()


embedding_service = EmbeddingService()
