import os
import sys
from pathlib import Path
# os.environ['FAISS_NO_AVX2'] = '1'

# 修复 Windows 上 faiss-cpu 的 DLL 加载问题
if sys.platform == "win32":
    # __file__ = .../backend/app/rag/index_manager.py
    # 需要向上 3 级到 backend，然后进入 .venv
    backend_dir = Path(__file__).resolve().parent.parent.parent
    faiss_libs = backend_dir / ".venv" / "Lib" / "site-packages" / "faiss_cpu.libs"
    if faiss_libs.exists() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(faiss_libs))

# 直接导入 swigfaiss_avx2 作为 faiss（绕过命名空间包问题）
import faiss
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
                print(f"[DEBUG] 加载后的 index 类型: {type(self.index).__name__}")
                print(f"[DEBUG] index 是否是 IndexFlatIP: {isinstance(self.index, faiss.IndexFlatIP)}")
                print(f"[DEBUG] index.ntotal: {self.index.ntotal if self.index else 'None'}")
                # 加防护：如果不是 FlatIP，强制重建
                if not isinstance(self.index, faiss.IndexFlatIP):
                    print(f"[WARNING] 检测到不兼容的 index 类型: {type(self.index).__name__}，强制重建 FlatIP")
                    self.index = faiss.IndexFlatIP(self.dim)
                else:
                    print(f"[INFO] 成功加载 IndexFlatIP，ntotal={self.index.ntotal}")
            except Exception as e:
                print(f"[ERROR] 读取 index 失败: {e}，强制新建 FlatIP")
                self.index = faiss.IndexFlatIP(self.dim)
        else:
            self.index = faiss.IndexFlatIP(self.dim)
            print(f"[DEBUG] 新建 IndexFlatIP, dim={self.dim}")


        # text_store 部分不变
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

        print("[DEBUG-add] type(vectors):", type(vectors))
        print("[DEBUG-add] vectors shape before np.array:",
              getattr(vectors, 'shape', 'no shape') if hasattr(vectors, 'shape') else "no attr")

        try:
            vectors_np = np.array(vectors).astype("float32")
            print("[DEBUG-add] vectors_np shape:", vectors_np.shape)
            print("[DEBUG-add] vectors_np dtype:", vectors_np.dtype)
            print("[DEBUG-add] ntotal before add:", self.index.ntotal)
        except Exception as e:
            print("[ERROR-add] 转换 vectors 失败:", str(e))
            raise

        if vectors_np.ndim != 2 or vectors_np.shape[1] != self.dim:
            raise ValueError(f"vectors 形状错误: {vectors_np.shape}, 预期 (n, {self.dim})")

        # self.index.add(vectors_np)  # 注意：这里用 vectors_np 而不是原 vectors
        self.text_store.extend(texts)
        print("[DEBUG-add] add 成功, ntotal now:", self.index.ntotal)

    # =========================
    # 检索
    # =========================
    def search(self, query_vec, kb_id, top_k=5):
        self.load(kb_id)

        if self.index.ntotal == 0:
            return []

        # 添加归一化（确保 query 与 index 的向量在同一尺度）
        query_vec = faiss.normalize_L2(query_vec.reshape(1, -1))  # ← 加这行

        D, I = self.index.search(query_vec, top_k)

        results = []
        for idx in I[0]:
            if idx < 0:
                continue
            if idx >= len(self.text_store):
                continue
            results.append(self.text_store[idx])

        return results