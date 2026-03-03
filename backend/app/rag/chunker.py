# app/rag/chunker.py
import re

def chunk_text(text, chunk_size=500, overlap=50):
    sentences = re.split(r'(?<=[\n。！？；])', text)  # 按句子/段落切
    chunks = []
    current_chunk = ""
    for sent in sentences:
        if len(current_chunk) + len(sent) <= chunk_size:
            current_chunk += sent
        else:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-overlap:] + sent  # overlap 后半部分
    if current_chunk:
        chunks.append(current_chunk.strip())
    # 修改：返回带chunk_id的list[dict]
    return [{"text": c, "chunk_id": i} for i, c in enumerate([c for c in chunks if c])]