# backend/app/services/kb_service.py
import json
import logging
import mimetypes
import shutil
from pathlib import Path
from datetime import datetime
import time
import uuid

from app.config.settings import PROJECT_ROOT

KB_ROOT = PROJECT_ROOT / "knowledge_base"
KB_ROOT.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)

def _now():
    return datetime.utcnow().isoformat()


class KBService:
    def __init__(self):
        KB_ROOT.mkdir(parents=True, exist_ok=True)

    def _generate_uuid_v7(self) -> str:
        """
        生成 UUID v7（时间有序 + 随机）
        """
        timestamp_ms = int(time.time() * 1000)
        ts_bytes = timestamp_ms.to_bytes(6, 'big')
        rand_bytes = uuid.uuid4().bytes

        uuid_bytes = bytearray(16)
        uuid_bytes[0:6] = ts_bytes
        uuid_bytes[6] = 0x70 | (rand_bytes[0] & 0x0f)
        uuid_bytes[7:10] = rand_bytes[1:4]
        uuid_bytes[10] = 0x80 | (rand_bytes[4] & 0x3f)
        uuid_bytes[11:16] = rand_bytes[5:10]

        return str(uuid.UUID(bytes=bytes(uuid_bytes)))

    def _kb_path(self, kb_id: str) -> Path:
        return KB_ROOT / kb_id

    def _meta_path(self, kb_id: str) -> Path:
        return self._kb_path(kb_id) / "kb_meta.json"

    # -----------------------------
    # 创建知识库
    # -----------------------------
    def create(self, display_name: str, system_prompt: str = "", description: str = ""):
        if not display_name or not display_name.strip():
            raise ValueError("知识库名称不能为空")

        kb_id = self._generate_uuid_v7()
        kb_path = self._kb_path(kb_id)

        if kb_path.exists():
            raise ValueError("知识库已存在")

        (kb_path / "files").mkdir(parents=True)
        (kb_path / "vector_store").mkdir(exist_ok=True)

        default_model = "bge-small-zh-v1.5"
        try:
            from app.services.embedding_factory import get_embedding_service
            svc = get_embedding_service(default_model)
            embedding_dim = svc.dim
        except Exception as e:
            logger.warning(f"无法自动获取默认模型维度，使用 512: {e}")
            embedding_dim = 512

        meta = {
            "kb_id": kb_id,
            "display_name": display_name.strip(),
            "description": description.strip(),
            "system_prompt": system_prompt.strip(),
            "created_at": _now(),
            "updated_at": _now(),
            "embedding_model": default_model,
            "embedding_dim": embedding_dim,  # ← 自动
            "last_embedding_model": None,
            "last_embedding_dim": None,
            "files": []
        }

        with open(self._meta_path(kb_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    # -----------------------------
    # 获取单个 KB
    # -----------------------------
    def get(self, kb_id: str):
        meta_path = self._meta_path(kb_id)
        if not meta_path.exists():
            return None

        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # -----------------------------
    # 列出所有 KB
    # -----------------------------
    def list(self):
        result = []
        for kb_dir in KB_ROOT.iterdir():
            if not kb_dir.is_dir():
                continue

            meta_file = kb_dir / "kb_meta.json"
            if meta_file.exists():
                with open(meta_file, "r", encoding="utf-8") as f:
                    result.append(json.load(f))
        return result

    # -----------------------------
    # 删除 KB（单个）
    # -----------------------------
    def delete(self, kb_id: str):
        kb_path = self._kb_path(kb_id)
        if kb_path.exists():
            shutil.rmtree(kb_path)
            return True
        return False

    # -----------------------------
    # 重命名 KB（专用方法）
    # -----------------------------
    def rename(self, kb_id: str, new_display_name: str):
        meta_path = self._meta_path(kb_id)
        if not meta_path.exists():
            raise ValueError("知识库不存在")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        new_name = new_display_name.strip()
        if not new_name:
            raise ValueError("新名称不能为空")

        meta["display_name"] = new_name
        meta["updated_at"] = _now()

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    # -----------------------------
    # 更新 system_prompt（专用方法）
    # -----------------------------
    def update_prompt(self, kb_id: str, new_system_prompt: str):
        meta_path = self._meta_path(kb_id)
        if not meta_path.exists():
            raise ValueError("知识库不存在")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta["system_prompt"] = new_system_prompt.strip()
        meta["updated_at"] = _now()

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    # -----------------------------
    # 通用更新（支持部分字段）
    # -----------------------------
    def update(self, kb_id: str,
               display_name: str = None,
               system_prompt: str = None,
               description: str = None,
               embedding_model: str = None,  # ← 新增这个参数
               embedding_dim: int = None):  # ← 可选也加这个
        meta_path = self._meta_path(kb_id)
        if not meta_path.exists():
            raise ValueError("知识库不存在")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        updated = False

        if display_name is not None:
            new_name = display_name.strip()
            if new_name:
                meta["display_name"] = new_name
                updated = True

        if system_prompt is not None:
            meta["system_prompt"] = system_prompt.strip()
            updated = True

        if description is not None:
            meta["description"] = description.strip()
            updated = True

        # 新增：支持更新 embedding_model
        if embedding_model is not None:
            cleaned_model = embedding_model.strip()
            if cleaned_model:
                meta["embedding_model"] = cleaned_model
                updated = True

        # 可选：支持直接更新 dim（但通常由系统自动算）
        if embedding_dim is not None:
            try:
                meta["embedding_dim"] = int(embedding_dim)
                updated = True
            except:
                pass

        if not updated:
            raise ValueError("没有提供任何要更新的字段")

        meta["updated_at"] = _now()

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    def update_last_embedding_info(self, kb_id: str, model_name: str, dim: int):
        meta = self.get(kb_id)
        if not meta:
            return
        meta["last_embedding_model"] = model_name
        meta["last_embedding_dim"] = dim
        meta["updated_at"] = _now()
        with open(self._meta_path(kb_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    # -----------------------------
    # 保存文件到知识库（由 upload_service 调用）
    # 返回更新后的 meta
    # -----------------------------
    def save_file(self, kb_id: str, file_storage):
        meta_path = self._meta_path(kb_id)
        if not meta_path.exists():
            raise ValueError("知识库不存在")

        filename = file_storage.filename
        if not filename:
            raise ValueError("无效文件名")

        ext = Path(filename).suffix.lower()
        if not ext:
            raise ValueError("文件缺少扩展名")

        kb_file_id = self._generate_uuid_v7()
        today = datetime.now().strftime("%Y-%m-%d")
        sub_dir = f"files/{today}/{ext.lstrip('.')}"
        save_dir = self._kb_path(kb_id) / sub_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        save_path = save_dir / f"{kb_file_id}{ext}"
        file_storage.save(save_path)

        # 相对路径（从 knowledge_base/ 开始）
        relative_path = save_path.relative_to(KB_ROOT.parent).as_posix()
        relative_path = f"/{relative_path}"  # 统一以 / 开头

        file_info = {
            "kb_file_id": kb_file_id,
            "filename": filename,
            "path": relative_path,
            "bytes": save_path.stat().st_size,
            "created_at": _now(),
            "mime_type": mimetypes.guess_type(str(save_path))[0] or "application/octet-stream"
        }

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta["files"].append(file_info)
        meta["updated_at"] = _now()

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    # -----------------------------
    # 删除单个文件（带备份回滚）
    # -----------------------------
    def delete_file(self, kb_id: str, kb_file_id: str) -> dict:
        meta_path = self._meta_path(kb_id)
        if not meta_path.exists():
            raise ValueError("知识库不存在")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        files = meta.get("files", [])
        found_index = -1
        for i, f in enumerate(files):
            if f.get("kb_file_id") == kb_file_id:
                found_index = i
                break
        if found_index == -1:
            raise ValueError(f"文件不存在: {kb_file_id}")

        file_info = files[found_index]
        relative_path = file_info["path"].lstrip("/")
        file_path = PROJECT_ROOT / relative_path

        backup_path = None
        if file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            file_path.rename(backup_path)

        # 更新 meta
        files.pop(found_index)
        meta["updated_at"] = _now()

        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if backup_path and backup_path.exists():
                try:
                    backup_path.rename(file_path)
                except Exception:
                    pass
            raise RuntimeError(f"更新 meta 失败: {str(e)}")

        if backup_path and backup_path.exists():
            try:
                backup_path.unlink()
            except Exception:
                pass

        return {
            "kb_id": kb_id,
            "kb_file_id": kb_file_id,
            "deleted": True
        }

    # -----------------------------
    # 批量删除文件（带备份回滚）
    # -----------------------------
    def batch_delete_files(self, kb_id: str, kb_file_ids: list) -> dict:
        if not kb_file_ids:
            raise ValueError("kb_file_ids 不能为空")

        meta_path = self._meta_path(kb_id)
        if not meta_path.exists():
            raise ValueError("知识库不存在")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        files = meta.get("files", [])

        targets = []
        for kb_file_id in kb_file_ids:
            found_index = -1
            found_file = None
            for i, f in enumerate(files):
                if f.get("kb_file_id") == kb_file_id:
                    found_index = i
                    found_file = f
                    break
            if found_index == -1:
                raise ValueError(f"文件不存在: {kb_file_id}")
            targets.append((found_index, found_file))

        backups = []
        try:
            for _, file_info in targets:
                relative_path = file_info["path"].lstrip("/")
                file_path = PROJECT_ROOT / relative_path
                if file_path.exists():
                    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                    file_path.rename(backup_path)
                    backups.append((file_path, backup_path))
        except Exception as e:
            for orig_path, bak_path in backups:
                if bak_path.exists():
                    try:
                        bak_path.rename(orig_path)
                    except Exception:
                        pass
            raise RuntimeError(f"备份文件失败: {str(e)}")

        original_files = meta["files"].copy()
        for index, _ in sorted(targets, key=lambda x: x[0], reverse=True):
            meta["files"].pop(index)
        meta["updated_at"] = _now()

        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            meta["files"] = original_files
            meta["updated_at"] = _now()
            try:
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception as rollback_error:
                raise RuntimeError(f"更新 meta 失败: {str(e)}，且回滚 meta 失败: {str(rollback_error)}")

            for orig_path, bak_path in backups:
                if bak_path.exists():
                    try:
                        bak_path.rename(orig_path)
                    except Exception:
                        pass
            raise RuntimeError(f"更新 meta 失败，已回滚: {str(e)}")

        for _, bak_path in backups:
            if bak_path.exists():
                try:
                    bak_path.unlink()
                except Exception:
                    pass

        return {
            "kb_id": kb_id,
            "deleted_count": len(kb_file_ids),
            "kb_file_ids": kb_file_ids,
            "deleted": True
        }


kb_service = KBService()