# backend/app/services/upload_service.py
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime

from app.config.settings import PROJECT_ROOT
from app.services.rag_service import rag_service
from app.rag.parser import DocumentParser


ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}

KB_ROOT = PROJECT_ROOT / "knowledge_base"
KB_ROOT.mkdir(parents=True, exist_ok=True)


class UploadService:
    def __init__(self):
        self.parser = DocumentParser()

    # -----------------------------
    # 校验
    # -----------------------------
    def validate_extension(self, filename: str):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("不允许的文件类型")

    def validate_mime(self, file_path: Path):
        mime, _ = mimetypes.guess_type(str(file_path))
        if mime and not (
            mime.startswith("text") or mime == "application/pdf"
        ):
            raise ValueError("文件 MIME 类型不合法")

    # -----------------------------
    # KB 文件保存路径
    # -----------------------------
    def build_kb_file_path(self, kb_id: str, ext: str) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")

        save_dir = (
            KB_ROOT
            / kb_id
            / "tmp"
            / today
            / ext.lstrip(".")
        )

        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    # -----------------------------
    # 主上传流程
    # -----------------------------
    def save_and_index(self, file_storage, kb_id=None):
        """
        完整 KB 上传 + 向量入库流水线
        """
        # 默认知识库
        if not kb_id:
            kb_id = "default"

        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        # 1. 扩展名检查
        self.validate_extension(filename)

        ext = Path(filename).suffix.lower()

        # 2. 构造保存路径
        save_dir = self.build_kb_file_path(kb_id, ext)
        file_id = uuid.uuid4().hex
        save_path = save_dir / f"{file_id}{ext}"

        # 3. 保存文件
        file_storage.save(save_path)

        # 4. MIME 检查
        self.validate_mime(save_path)

        # 5. 文本解析
        text = self.parser.parse(save_path)

        if not text or not text.strip():
            raise ValueError("文件解析为空")

        # 6. RAG 入库
        rag_service.ingest_text(text, kb_id=kb_id)

        return {
            "file_id": file_id,
            "kb_id": kb_id,
            "filename": filename,
            "path": str(save_path),
        }


upload_service = UploadService()