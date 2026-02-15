# app/rag/parser.py
from pathlib import Path


class DocumentParser:
    """
    统一文档解析入口
    后续扩展 PDF、OCR 都在这里加
    """

    def parse(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()

        if ext in [".txt", ".md"]:
            return self._parse_text(file_path)

        raise ValueError(f"不支持的文件类型: {ext}")

    def _parse_text(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8", errors="ignore")
