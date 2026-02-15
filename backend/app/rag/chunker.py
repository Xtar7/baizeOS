# app/rag/chunker.py
def chunk_text(text, chunk_size=500, overlap=50):
    """
    简单文本切分
    """
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks
