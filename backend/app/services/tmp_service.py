# backend/app/services/tmp_service.py
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime

from app.config.settings import PROJECT_ROOT


DATA_ROOT = PROJECT_ROOT / "data"
DATA_ROOT.mkdir(parents=True, exist_ok=True)


class TmpService:
    def __init__(self):
        pass

    def _build_path(self, chat_id: str, ext: str) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        save_dir = DATA_ROOT / today / chat_id / ext.lstrip(".")
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    def tmp_upload(self, chat_id: str, file_storage):
        """
        上传临时文件到特定对话的目录
        """
        if not chat_id or not chat_id.strip():
            raise ValueError("缺少 chat_id")

        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        ext = Path(filename).suffix.lower()
        if not ext:
            raise ValueError("文件缺少扩展名")

        file_id = uuid.uuid4().hex
        save_dir = self._build_path(chat_id.strip(), ext)
        save_path = save_dir / f"{file_id}{ext}"

        file_storage.save(save_path)

        mime, _ = mimetypes.guess_type(str(save_path))

        return {
            "id": file_id,
            "object": "file",
            "chat_id": chat_id,
            "filename": filename,
            "bytes": save_path.stat().st_size,
            "created_at": int(datetime.now().timestamp()),
            "path": str(save_path),
            "mime_type": mime,
        }

    def tmp_list(self, chat_id: str = None):
        """
        列出临时文件，可选按 chat_id 过滤
        """
        files = []

        if chat_id:
            base = DATA_ROOT.glob(f"*/{chat_id}")
        else:
            base = DATA_ROOT.rglob("*.*")

        for path in base:
            if path.is_file():
                files.append({
                    "id": path.stem,
                    "object": "file",
                    "filename": path.name,
                    "bytes": path.stat().st_size,
                    "created_at": int(path.stat().st_ctime),
                    "path": str(path),
                })

        return files

    def tmp_delete(self, file_id: str):
        """
        删除单个临时文件（全局查找）
        """
        for path in DATA_ROOT.rglob(f"{file_id}.*"):
            if path.is_file():
                path.unlink()
                return True
        return False

    def tmp_delete_by_chat(self, chat_id: str):
        """
        删除某个对话的所有临时文件
        """
        count = 0
        for path in DATA_ROOT.rglob("*"):
            if path.is_file() and chat_id in path.parts:
                path.unlink()
                count += 1
        return count


tmp_service = TmpService()