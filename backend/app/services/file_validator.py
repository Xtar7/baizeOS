# backend/app/services/file_validator.py（新增）
"""文件校验器：负责扩展名、MIME、大小等校验"""
import mimetypes
from pathlib import Path


class FileValidator:
    ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
    ALLOWED_MIME_PREFIXES = ("text/", "application/pdf")

    def validate_extension(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型，仅允许 {self.ALLOWED_EXTENSIONS}")
        return True

    def validate_mime(self, file_path: Path) -> bool:
        mime, _ = mimetypes.guess_type(str(file_path))
        if mime and not any(mime.startswith(p) for p in self.ALLOWED_MIME_PREFIXES):
            raise ValueError("文件 MIME 类型不合法")
        return True

    def validate_size(self, file_path: Path, max_mb: int = 100) -> bool:
        """校验文件大小，超出则抛出异常"""
        if file_path.stat().st_size > max_mb * 1024 * 1024:
            raise ValueError(f"文件过大 ({file_path.stat().st_size} bytes)，最大允许 {max_mb}MB")
        return True
