# app/rag/retriever.py
from pathlib import Path

# 知识库根目录
KB_ROOT = Path("knowledge_base")


class Retriever:
    def search(self, query, kb_id, top_k=3):
        """
        最简版检索：
        从 docs.txt 中按关键词返回前 top_k 行
        """

        kb_path = KB_ROOT / kb_id / "docs.txt"

        if not kb_path.exists():
            return ["（知识库为空）"]

        lines = kb_path.read_text(encoding="utf-8").splitlines()

        # 简单关键词匹配
        results = []
        for line in lines:
            if any(word in line for word in query.split()):
                results.append(line)

        if not results:
            results = lines[:top_k]

        return results[:top_k]


# 全局单例
retriever = Retriever()