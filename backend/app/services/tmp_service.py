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

    # -----------------------------
    # 构建存储路径
    # -----------------------------
    def tmp_build_path(self, ext: str) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        save_dir = DATA_ROOT / today / ext.lstrip(".")
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    # -----------------------------
    # 上传文件
    # -----------------------------
    def tmp_upload(self, file_storage):
        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        ext = Path(filename).suffix.lower()
        if not ext:
            raise ValueError("文件缺少扩展名")

        file_id = uuid.uuid4().hex
        save_dir = self.tmp_build_path(ext)
        save_path = save_dir / f"{file_id}{ext}"

        file_storage.save(save_path)

        mime, _ = mimetypes.guess_type(str(save_path))

        return {
            "id": file_id,
            "object": "file",
            "filename": filename,
            "bytes": save_path.stat().st_size,
            "created_at": int(datetime.now().timestamp()),
            "path": str(save_path),
            "mime_type": mime,
        }

    # -----------------------------
    # 列出所有文件
    # -----------------------------
    def tmp_list(self):
        files = []

        for path in DATA_ROOT.rglob("*.*"):
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

    # -----------------------------
    # 删除文件
    # -----------------------------
    def tmp_delete(self, file_id: str):
        for path in DATA_ROOT.rglob(f"{file_id}.*"):
            if path.is_file():
                path.unlink()
                return True
        return False


tmp_service = TmpService()