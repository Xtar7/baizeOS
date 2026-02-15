# app/services/rag_service.py
from app.services.llm_service import llm_service
from app.rag.retriever import retriever


class RAGService:
    def rag_chat(self, messages, kb_id=None, stream=False, model=None, prompt_name="default"):
        """
        RAG 主入口
        """

        if not kb_id:
            raise RuntimeError("rag=true 时必须提供 kb_id")

        if not messages:
            raise RuntimeError("messages 不能为空")

        question = messages[-1]["content"]

        # 1. 检索知识
        docs = retriever.search(question, kb_id=kb_id)

        context = "\n".join(docs) if docs else "（未检索到相关资料）"

        # 2. 构造 RAG prompt
        rag_prompt = f"""
你是一个知识库问答助手。
请仅根据以下资料回答问题，不要编造内容。

【资料】
{context}

【问题】
{question}
"""

        new_messages = [
            {"role": "system", "content": rag_prompt},
            {"role": "user", "content": question},
        ]

        # 3. 调用 LLM
        return llm_service.completions(
            messages=new_messages,
            stream=stream,
            model=model,
            prompt_name=prompt_name,
        )


# 全局单例
rag_service = RAGService()