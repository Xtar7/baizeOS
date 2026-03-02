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
from app.config.settings import KB_DIR

class IndexManager:
    def __init__(self, dim):
        self.dim = dim
        self.index = None
        self.text_store = []
        self.current_kb = None

    # =========================
    # 路径管理
    # =========================
    def _get_kb_paths(self, kb_id):
        kb_root = KB_DIR / kb_id
        vector_dir = kb_root / "vector_store"
        vector_dir.mkdir(parents=True, exist_ok=True)

        index_path = vector_dir / "index.faiss"
        store_path = vector_dir / "text_store.pkl"

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

        # 加载 text_store
        if store_path.exists():
            with open(store_path, "rb") as f:
                self.text_store = pickle.load(f)
        else:
            self.text_store = []

        self.current_kb = kb_id

    # =========================
    # 保存
    # =========================
    def save(self, kb_id):
        index_path, store_path = self._get_kb_paths(kb_id)

        faiss.write_index(self.index, str(index_path))

        with open(store_path, "wb") as f:
            pickle.dump(self.text_store, f)

    # =========================
    # 添加向量
    # =========================
    def add(self, vectors, texts, kb_id):
        self.load(kb_id)

        try:
            vectors_np = np.array(vectors).astype("float32")
        except Exception as e:
            raise e

        if vectors_np.ndim != 2 or vectors_np.shape[1] != self.dim:
            raise ValueError(f"vectors 形状错误: {vectors_np.shape}, 预期 (n, {self.dim})")

        # 注意：保持你原有逻辑，不恢复 add
        self.index.add(vectors_np)
        self.text_store.extend(texts)

    # =========================
    # 检索
    # =========================
    def search(self, query_vec, kb_id, top_k=5):
        self.load(kb_id)

        # 添加调试打印：输出 index 状态
        logger.info(f"[INDEX DEBUG] Loaded KB {kb_id}: total vectors = {self.index.ntotal}")

        if self.index.ntotal == 0:
            logger.warning(f"[INDEX DEBUG] Index for KB {kb_id} is empty! No results.")
            return []

        query_vec = query_vec.astype("float32").reshape(1, -1)
        faiss.normalize_L2(query_vec)

        D, I = self.index.search(query_vec, top_k)

        results = []
        for idx in I[0]:
            if 0 <= idx < len(self.text_store):
                results.append(self.text_store[idx])

        # 添加调试打印：输出实际结果
        if results:
            logger.info(f"[INDEX DEBUG] Found {len(results)} matching chunks (top_k={top_k})")
            logger.debug(f"[INDEX DEBUG] First result preview: {results[0][:100]}...")
        else:
            logger.warning(f"[INDEX DEBUG] No matching chunks found (distances: {D[0] if D.size > 0 else 'N/A'})")

        return results