# backend/app/services/rag_service.py
import json
import logging
from app.config.settings import PROJECT_ROOT
from app.rag.index_manager import IndexManager
from app.rag.retriever import Retriever
from app.services.llm_service import llm_service
from app.services.kb_service import kb_service
from app.services.embedding_service import get_embedding_service  # ← 关键导入
from app.rag.chunker import chunk_text
from app.config.settings import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)
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
        """
        完整 ingest 流程：读取 meta → 选模型 → chunk → embed → add → 更新 last_
        """
        if not text or not text.strip():
            logger.warning(f"KB {kb_id} ingest 文本为空，跳过")
            return {"ingested": 0, "chunks": 0, "model_used": None}

        if not kb_id:
            kb_id = "default"

        # 1. 获取 KB meta
        meta = kb_service.get(kb_id)
        if not meta:
            raise ValueError(f"知识库 {kb_id} 不存在")

        target_model = meta.get("embedding_model", "bge-small-zh-v1.5")

        # 2. 获取 embedding 服务（全局缓存，延迟加载）
        try:
            embedding_svc = get_embedding_service(target_model)
            actual_dim = embedding_svc.dim
        except Exception as e:
            logger.error(f"加载 embedding 模型失败: {str(e)}")
            raise RuntimeError(f"无法加载模型 {target_model}: {str(e)}")

        # 3. 切分文本
        try:
            chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        except Exception as e:
            logger.error(f"文本切分失败: {str(e)}")
            raise

        if not chunks:
            logger.warning(f"KB {kb_id} 切分后无有效 chunk，跳过")
            return {"ingested": 0, "chunks": 0, "model_used": target_model}

        # 4. 生成向量（支持批量）
        try:
            vectors = embedding_svc.embed(chunks)  # embed 已支持 list[str]
            if len(vectors) != len(chunks):
                raise RuntimeError("向量数量与 chunk 不匹配")
            if vectors.shape[1] != actual_dim:
                raise RuntimeError(f"维度不匹配：预期 {actual_dim}，实际 {vectors.shape[1]}")
        except Exception as e:
            logger.error(f"生成向量失败: {str(e)}")
            raise

        # 5. 添加到 index
        try:
            index_manager = IndexManager(dim=actual_dim)
            index_manager.add(vectors, chunks, kb_id)
            index_manager.save(kb_id)
        except Exception as e:
            logger.error(f"向量入库失败: {str(e)}")
            raise

        # 6. 更新 last_embedding 信息
        try:
            kb_service.update_last_embedding_info(
                kb_id=kb_id,
                model_name=target_model,
                dim=int(actual_dim)
            )
        except Exception as e:
            logger.warning(f"更新 last_embedding 信息失败，但 ingest 已成功: {str(e)}")
            # 不抛异常

        logger.info(f"KB {kb_id} ingest 成功：{len(chunks)} chunks，使用模型 {target_model}")

        return {
            "ingested": 1,
            "chunks": len(chunks),
            "model_used": target_model,
            "dim": actual_dim
        }

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