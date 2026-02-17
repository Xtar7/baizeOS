# backend/app/services/tmp_service.py
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime

from app.config.settings import PROJECT_ROOT

BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_ROOT = BACKEND_ROOT / "data"
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

        tmp_file_id = uuid.uuid4().hex
        save_dir = self._build_path(chat_id.strip(), ext)
        save_path = save_dir / f"{tmp_file_id}{ext}"

        file_storage.save(save_path)

        mime, _ = mimetypes.guess_type(str(save_path))

        return {
            "tmp_file_id": tmp_file_id,
            "object": "file",
            "chat_id": chat_id,
            "filename": filename,
            "bytes": save_path.stat().st_size,
            "created_at": int(datetime.now().timestamp()),
            "path": f"/{save_path.relative_to(DATA_ROOT.parent).as_posix()}",
            "mime_type": mime,
        }

    def tmp_list(self, chat_id: str = None):
        """
        列出临时文件，支持按 chat_id 过滤
        返回的 path 从 /data/ 开始的相对路径
        """
        files = []

        if chat_id:
            chat_id_clean = chat_id.strip()
            # 先找到所有日期目录下匹配 chat_id 的子目录
            date_dirs = [p for p in DATA_ROOT.iterdir() if p.is_dir()]
            target_dirs = []
            for date_dir in date_dirs:
                candidate = date_dir / chat_id_clean
                if candidate.is_dir():
                    target_dirs.append(candidate)

            # 对每个匹配的 chat_id 目录进行递归查找文件
            for target_dir in target_dirs:
                for file_path in target_dir.rglob("*.*"):
                    if file_path.is_file():
                        # 计算相对路径：从 data/ 开始
                        try:
                            rel_path = file_path.relative_to(DATA_ROOT.parent)  # 去掉 backend/，得到 data/...
                            rel_path_str = f"/{rel_path.as_posix()}"  # 用 / 分隔，前面加 /
                        except ValueError:
                            rel_path_str = str(file_path)  # 兜底用绝对路径

                        files.append({
                            "tmp_file_id": file_path.stem,
                            "object": "file",
                            "filename": file_path.name,
                            "bytes": file_path.stat().st_size,
                            "created_at": int(file_path.stat().st_ctime),
                            "path": rel_path_str,  # 现在是 /data/2026-02-17/.../xxx.txt
                            "mime_type": mimetypes.guess_type(str(file_path))[0] or "application/octet-stream",
                        })
        else:
            # 无 chat_id 时，列出所有（可选加限制，避免过多）
            for file_path in DATA_ROOT.rglob("*.*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(DATA_ROOT.parent)
                    rel_path_str = f"/{rel_path.as_posix()}"
                    files.append({
                        "tmp_file_id": file_path.stem,
                        "object": "file",
                        "filename": file_path.name,
                        "bytes": file_path.stat().st_size,
                        "created_at": int(file_path.stat().st_ctime),
                        "path": rel_path_str,
                        "mime_type": mimetypes.guess_type(str(file_path))[0] or "application/octet-stream",
                    })

        # 按创建时间倒序
        files_sorted = sorted(files, key=lambda x: x.get("created_at", 0), reverse=True)

        return files_sorted

    def delete_file(self, chat_id: str, tmp_file_id: str) -> bool:
        """
        删除指定 chat_id 下的单个临时文件
        必须同时匹配 chat_id 和 tmp_file_id 才能删除
        返回是否成功删除
        """
        chat_id_clean = chat_id.strip()
        tmp_file_id_clean = tmp_file_id.strip()

        deleted = False

        for path in DATA_ROOT.rglob(f"{tmp_file_id_clean}.*"):
            if path.is_file():
                # 严格检查路径中是否包含该 chat_id（防止误删其他对话的文件）
                path_parts = [p.strip() for p in path.parts]
                if chat_id_clean in path_parts:
                    try:
                        path.unlink()
                        deleted = True
                    except Exception as e:
                        print(f"[ERROR] 删除文件失败 {path}: {e}")
                        continue

        return deleted


tmp_service = TmpService()