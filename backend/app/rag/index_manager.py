# app/rag/index_manager.py
import os
import sys
from pathlib import Path

# 修复 Windows 上 faiss-cpu 的 DLL 加载问题
if sys.platform == "win32":
    backend_dir = Path(__file__).resolve().parent.parent.parent
    faiss_libs = backend_dir / ".venv" / "Lib" / "site-packages" / "faiss_cpu.libs"
    if faiss_libs.exists() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(faiss_libs))

# 标准导入 faiss（移除 swigfaiss_avx2 的硬编码，让 faiss 自动处理后端）
import faiss  # 这会加载完整的包装层，包括 normalize_L2
import pickle
import numpy as np
from app.config.settings import KB_ROOT

class IndexManager:
    def __init__(self, dim):
        self.dim = dim
        self.index = None
        self.doc_store = []  # 修改：从text_store改为doc_store，存储list[dict] with "text" and "metadata"
        self.current_kb = None

    # =========================
    # 路径管理
    # =========================
    def _get_kb_paths(self, kb_id):
        kb_root = KB_ROOT / kb_id
        vector_dir = kb_root / "vector_store"
        vector_dir.mkdir(parents=True, exist_ok=True)

        index_path = vector_dir / "index.faiss"
        store_path = vector_dir / "doc_store.pkl"  # 修改：从text_store.pkl改为doc_store.pkl

        return index_path, store_path

    # =========================
    # 加载
    # =========================
    def load(self, kb_id):
        if self.current_kb == kb_id:
            return

        index_path, store_path = self._get_kb_paths(kb_id)

        if index_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))

                # 如果不是 IndexFlatIP，则强制重建
                if not isinstance(self.index, faiss.IndexFlatIP):
                    self.index = faiss.IndexFlatIP(self.dim)

            except Exception:
                self.index = faiss.IndexFlatIP(self.dim)
        else:
            self.index = faiss.IndexFlatIP(self.dim)

        # 加载 doc_store
        if store_path.exists():
            with open(store_path, "rb") as f:
                self.doc_store = pickle.load(f)
        else:
            self.doc_store = []

        self.current_kb = kb_id

    # =========================
    # 保存
    # =========================
    def save(self, kb_id):
        index_path, store_path = self._get_kb_paths(kb_id)

        faiss.write_index(self.index, str(index_path))

        with open(store_path, "wb") as f:
            pickle.dump(self.doc_store, f)

    # =========================
    # 添加向量
    # =========================
    def add(self, vectors, docs: list[dict], kb_id):  # 修改：texts -> docs: list[dict]
        self.load(kb_id)

        try:
            vectors_np = np.array(vectors).astype("float32")
        except Exception as e:
            raise e

        if vectors_np.ndim != 2 or vectors_np.shape[1] != self.dim:
            raise ValueError(f"vectors 形状错误: {vectors_np.shape}, 预期 (n, {self.dim})")

        # 注意：保持你原有逻辑，不恢复 add
        self.index.add(vectors_np)
        self.doc_store.extend(docs)  # 修改：extend docs (list[dict])

    # =========================
    # 检索
    # =========================
    def search(self, query_vec, kb_id, top_k=5):
        self.load(kb_id)

        query_vec = query_vec.astype("float32").reshape(1, -1)
        faiss.normalize_L2(query_vec)

        D, I = self.index.search(query_vec, top_k)

        results = []
        for i, idx in enumerate(I[0]):
            if 0 <= idx < len(self.doc_store):
                doc = self.doc_store[idx].copy()
                doc["score"] = float(D[0][i])
                results.append(doc)

        return results  # 修改：返回list[dict] with "text", "metadata", "score"