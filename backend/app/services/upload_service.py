# app/services/upload_service.py
import uuid
from pathlib import Path
import mimetypes
from datetime import datetime

from app.config.settings import PROJECT_ROOT
from app.services.rag_service import rag_service
from app.rag.parser import DocumentParser


ALLOWED_EXTENSIONS = {".txt", ".md"}

KB_ROOT = PROJECT_ROOT / "knowledge_base"
KB_ROOT.mkdir(parents=True, exist_ok=True)


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

    def _get_save_dir(self, kb_id: str) -> Path:
        """
        根据 kb_id 和日期生成保存目录
        knowledge_base/kb_id/files/yyyy-mm-dd/
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        save_dir = KB_ROOT / kb_id / "files" / date_str
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    def save_and_index(self, file_storage, kb_id=None):
        """
        完整上传流水线
        """
        # 默认知识库
        if not kb_id:
            kb_id = "default"

        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        # 1. 扩展名检查
        self.validate_extension(filename)

        # 2. 获取知识库存储目录
        save_dir = self._get_save_dir(kb_id)

        # 3. 随机文件名
        file_id = uuid.uuid4().hex
        ext = Path(filename).suffix.lower()
        save_path = save_dir / f"{file_id}{ext}"

        # 4. 保存文件
        file_storage.save(save_path)

        # 5. MIME 检查
        self.validate_mime(save_path)

        # 6. 文本解析
        text = self.parser.parse(save_path)

        if not text.strip():
            raise ValueError("文件内容为空或解析失败")

        # 7. 入库
        rag_service.ingest_text(text, kb_id=kb_id)

        return kb_id


upload_service = UploadService()