# app/services/upload_service.py
import uuid
from pathlib import Path
import mimetypes

from app.config.settings import PROJECT_ROOT
from app.services.rag_service import rag_service
from app.rag.parser import DocumentParser


ALLOWED_EXTENSIONS = {".txt", ".md"}
UPLOAD_ROOT = PROJECT_ROOT / "knowledge_base" / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


class UploadService:
    def __init__(self):
        self.parser = DocumentParser()

    def validate_extension(self, filename: str):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("不允许的文件类型")

    def validate_mime(self, file_path: Path):
        mime, _ = mimetypes.guess_type(str(file_path))
        if mime and not mime.startswith("text"):
            raise ValueError("文件 MIME 类型不合法")

    def save_and_index(self, file_storage):
        """
        完整上传流水线
        """
        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        # 1. 扩展名检查
        self.validate_extension(filename)

        # 2. 随机文件名
        file_id = uuid.uuid4().hex
        ext = Path(filename).suffix.lower()
        save_path = UPLOAD_ROOT / f"{file_id}{ext}"

        # 3. 保存文件
        file_storage.save(save_path)

        # 4. MIME 检查
        self.validate_mime(save_path)

        # 5. 文本解析
        text = self.parser.parse(save_path)

        # 6. 入库
        rag_service.ingest_text(text)

        return file_id


upload_service = UploadService()
