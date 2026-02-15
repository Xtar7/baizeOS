# app/services/rag_service.py
from app.rag.retriever import Retriever
from app.rag.chunker import chunk_text
from app.services.llm_service import LLMService


class RAGService:
    def __init__(self):
        self.retriever = Retriever()
        self.llm = LLMService()

    # -----------------------------
    # 0. 文本入库（upload用）
    # -----------------------------
    def ingest_text(self, text, kb_id):
        """
        文本 → 切分 → 向量化 → 入库
        """
        chunks = chunk_text(text)
        if not chunks:
            return 0

        self.retriever.add_documents(chunks, kb_id=kb_id)
        return len(chunks)

    # -----------------------------
    # 1. 向量检索
    # -----------------------------
    def retrieve_context(self, query, kb_id, top_k=3):
        return self.retriever.search(query, kb_id=kb_id, top_k=top_k)

    # -----------------------------
    # 2. 构造 RAG Prompt
    # -----------------------------
    def build_rag_messages(self, messages, kb_id):
        if not messages:
            return messages

        user_query = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content")
                break

        if not user_query or not kb_id:
            return messages

        contexts = self.retrieve_context(user_query, kb_id=kb_id)

        if not contexts:
            return messages

        context_text = "\n\n".join(contexts)

        system_prompt = {
            "role": "system",
            "content": (
                "You are a helpful assistant. "
                "Answer using the provided context. "
                "If the context is not relevant, answer normally.\n\n"
                f"Context:\n{context_text}"
            ),
        }

        return [system_prompt] + messages

    # -----------------------------
    # 3. RAG主流程
    # -----------------------------
    def rag_chat(self, messages, kb_id=None, model=None, stream=False, **kwargs):
        rag_messages = self.build_rag_messages(messages, kb_id=kb_id)

        # ⚠️ 改为调用 completions（你真实存在的方法）
        return self.llm.chat_completions(
            messages=rag_messages,
            model=model,
            stream=stream,
            **kwargs
        )


# 全局实例
rag_service = RAGService()