# app/rag/__init__.py
"""
RAG 模块的包初始化文件
只负责导出子模块中的核心类/函数，不执行任何初始化逻辑（如模型扫描），
避免循环导入问题。
"""

from .chunker import chunk_text
from .embedding import EmbeddingService
from .index_manager import IndexManager
from .retriever import Retriever, retriever  # 如果你有全局 retriever 实例

# 不再放任何导入 embedding_service 或 scan_embedding_models 的代码
# 也不放 RAGService 类定义（它应该放在 rag_service.py 里）