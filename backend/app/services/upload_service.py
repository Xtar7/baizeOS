# backend/app/services/upload_service.py
import mimetypes
from pathlib import Path

from app.config.settings import PROJECT_ROOT
from app.services.kb_service import kb_service
from app.services.rag_service import rag_service
from app.rag.parser import DocumentParser

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
from app.config.settings import KB_ROOT, KB_DIR
KB_ROOT.mkdir(parents=True, exist_ok=True)

class UploadService:
    def __init__(self):
        self.parser = DocumentParser()

    def validate_extension(self, filename: str):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型，仅允许 {ALLOWED_EXTENSIONS}")

    def validate_mime(self, file_path: Path):
        mime, _ = mimetypes.guess_type(str(file_path))
        if mime and not (mime.startswith("text/") or mime == "application/pdf"):
            raise ValueError("文件 MIME 类型不合法")

    def save_and_index(self, file_storage, kb_id: str = None):
        """
        KB 文件上传 + 向量入库完整流程
        现在委托 kb_service 进行实际存储
        """
        if not kb_id:
            kb_id = "default"

        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        # 校验扩展名
        self.validate_extension(filename)

        # 保存文件（委托给 kb_service）
        meta = kb_service.save_file(kb_id, file_storage)

        # 从 meta 中拿到最新保存的文件信息
        latest_file = meta["files"][-1]
        # ========== 修改：相对路径转绝对路径 ==========
        relative_path = latest_file["path"].lstrip("/")
        save_path = PROJECT_ROOT / relative_path  # 修复：移除 .parent，使用 PROJECT_ROOT
        # ============================================

        # MIME 校验
        self.validate_mime(save_path)

        # 文本解析
        text = self.parser.parse(save_path)

        if not text or not text.strip():
            raise ValueError("文件内容解析为空，无法向量化")

        # RAG 入库
        # 修改：传入file_id
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