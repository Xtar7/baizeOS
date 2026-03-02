import faiss
print(hasattr(faiss, "normalize_L2"))          # 应该输出 True
print(faiss.normalize_L2)                       # 应该显示 <function normalize_L2 ...>