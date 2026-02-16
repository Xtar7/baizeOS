# backend/app/services/rag_service.py
import json
from app.config.settings import PROJECT_ROOT
from app.rag.retriever import Retriever
from app.services.llm_service import llm_service


KB_ROOT = PROJECT_ROOT / "knowledge_base"


class RAGService:
    def __init__(self):
        self.retriever = Retriever()

    # -----------------------------
    # 读取 KB 的 system_prompt
    # -----------------------------
    def load_kb_prompt(self, kb_id: str) -> str:
        if not kb_id:
            return ""

        meta_path = KB_ROOT / kb_id / "kb_meta.json"
        if not meta_path.exists():
            return ""

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("system_prompt", "")
        except Exception:
            return ""

    # -----------------------------
    # 向量检索
    # -----------------------------
    def retrieve_context(self, query, kb_id, top_k=3):
        if not kb_id:
            return []
        return self.retriever.search(query, kb_id=kb_id, top_k=top_k)

    # -----------------------------
    # 构造 RAG messages
    # -----------------------------
    def build_rag_messages(self, messages, kb_id):
        if not messages:
            return messages

        # 获取用户最后一句话
        user_query = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content")
                break

        if not user_query:
            return messages

        contexts = self.retrieve_context(user_query, kb_id=kb_id)

        kb_prompt = self.load_kb_prompt(kb_id)

        system_parts = []

        if kb_prompt:
            system_parts.append(kb_prompt)

        if contexts:
            context_text = "\n\n".join(contexts)
            system_parts.append(
                "Use the following knowledge base context when relevant:\n"
                + context_text
            )

        if not system_parts:
            return messages

        system_prompt = {
            "role": "system",
            "content": "\n\n".join(system_parts),
        }

        return [system_prompt] + messages

    # -----------------------------
    # 入库（给 upload 调用）
    # -----------------------------
    def ingest_text(self, text: str, kb_id: str):
        if not kb_id:
            kb_id = "default"

        self.retriever.add_documents(
            texts=[text],
            kb_id=kb_id
        )

    # -----------------------------
    # RAG 主入口（兼容 chat_completions）
    # -----------------------------
    def rag_chat(self, messages, kb_id=None, stream=False, **kwargs):
        rag_messages = self.build_rag_messages(messages, kb_id=kb_id)

        # 直接复用原始 LLM 接口
        return llm_service.chat_completions(
            messages=rag_messages,
            stream=stream,
            **kwargs
        )


# 全局实例（供接口调用）
rag_service = RAGService()