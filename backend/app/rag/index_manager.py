import faiss
import pickle
from pathlib import Path
import numpy as np
from app.config.settings import KB_DIR


class IndexManager:
    def __init__(self, dim=768):
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
            self.index = faiss.read_index(str(index_path))
        else:
            self.index = faiss.IndexFlatL2(self.dim)

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

        vectors = np.array(vectors).astype("float32")
        self.index.add(vectors)
        self.text_store.extend(texts)

    # =========================
    # 检索
    # =========================
    def search(self, query_vec, kb_id, top_k=5):
        self.load(kb_id)

        if self.index.ntotal == 0:
            return []

        D, I = self.index.search(query_vec, top_k)

        results = []
        for idx in I[0]:
            if idx < 0:
                continue
            if idx >= len(self.text_store):
                continue
            results.append(self.text_store[idx])

        return results