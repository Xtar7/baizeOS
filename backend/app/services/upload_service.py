# backend/app/services/upload_service.py
import mimetypes
from pathlib import Path

from app.config.settings import PROJECT_ROOT, MAX_UPLOAD_SIZE_MB
from app.services.kb_service import kb_service
from app.services.rag_service import rag_service
from app.rag.parser import DocumentParser
from app.services.file_validator import FileValidator


class UploadService:
    def __init__(self):
        self.parser = DocumentParser()
        self.validator = FileValidator()

    def save_and_index(self, file_storage, kb_id: str = None):
        """
        KB 文件上传 + 向量入库完整流程
        委托 kb_service 进行实际存储
        """
        if not kb_id:
            kb_id = "default"

        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        # 1. 校验扩展名
        self.validator.validate_extension(filename)

        # 2. 保存文件（委托给 kb_service）
        meta = kb_service.save_file(kb_id, file_storage)

        # 从 meta 中拿到最新保存的文件信息
        latest_file = meta["files"][-1]
        relative_path = latest_file["path"].lstrip("/")
        save_path = PROJECT_ROOT / relative_path

        # 3. 文件存在性检查
        if not save_path.exists():
            raise FileNotFoundError(f"文件保存后不存在: {save_path}")

        # 4. 文件大小校验
        self.validator.validate_size(save_path, max_mb=MAX_UPLOAD_SIZE_MB)

        # 5. MIME 校验
        self.validator.validate_mime(save_path)

        # 6. 文本解析
        text = self.parser.parse(save_path)

        if not text or not text.strip():
            raise ValueError("文件内容解析为空，无法向量化")

        # 7. RAG 入库
        rag_service.ingest_text(text, kb_id=kb_id, file_id=latest_file["kb_file_id"])

        return {
            "kb_file_id": latest_file["kb_file_id"],
            "kb_id": kb_id,
            "filename": filename,
            "path": str(latest_file["path"]),
            "bytes": save_path.stat().st_size,
            "created_at": latest_file["created_at"]
        }

upload_service = UploadService()
