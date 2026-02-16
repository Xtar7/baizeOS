# backend/app/services/kb_service.py
import json
import shutil
from pathlib import Path
from datetime import datetime

from app.config.settings import PROJECT_ROOT

KB_ROOT = PROJECT_ROOT / "knowledge_base"


def _now():
    return datetime.utcnow().isoformat()


class KBService:
    def __init__(self):
        # 确保 knowledge_base 目录存在
        KB_ROOT.mkdir(parents=True, exist_ok=True)

    def _kb_path(self, kb_name: str):
        return KB_ROOT / f"kb_{kb_name}"

    def _meta_path(self, kb_name: str):
        return self._kb_path(kb_name) / "kb_meta.json"

    # -----------------------------
    # 创建 workspace / 知识库
    # -----------------------------
    def create(self, kb_name: str, system_prompt: str = "", description: str = ""):
        kb_path = self._kb_path(kb_name)

        if kb_path.exists():
            raise ValueError("知识库已存在")

        # 创建目录结构
        (kb_path / "tmp").mkdir(parents=True)
        (kb_path / "vector_store").mkdir()

        meta = {
            "id": f"kb_{kb_name}",
            "name": kb_name,
            "description": description,
            "system_prompt": system_prompt,
            "created_at": _now(),
            "updated_at": _now(),
            "tmp": []
        }

        with open(self._meta_path(kb_name), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    # -----------------------------
    # 获取单个 KB
    # -----------------------------
    def get(self, kb_name: str):
        meta_path = self._meta_path(kb_name)
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
    # 删除 KB
    # -----------------------------
    def delete(self, kb_name: str):
        kb_path = self._kb_path(kb_name)
        if kb_path.exists():
            shutil.rmtree(kb_path)
            return True
        return False

    # -----------------------------
    # 更新 workspace prompt
    # -----------------------------
    def update_prompt(self, kb_name: str, system_prompt: str):
        meta_path = self._meta_path(kb_name)
        if not meta_path.exists():
            raise ValueError("知识库不存在")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta["system_prompt"] = system_prompt
        meta["updated_at"] = _now()

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    # -----------------------------
    # 保存文件到 KB
    # -----------------------------
    def save_file(self, kb_name: str, file_storage):
        kb_path = self._kb_path(kb_name)
        if not kb_path.exists():
            raise ValueError("知识库不存在")

        filename = file_storage.filename
        ext = Path(filename).suffix.lower().lstrip(".")
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

        save_dir = kb_path / "tmp" / date_str / ext
        save_dir.mkdir(parents=True, exist_ok=True)

        file_id = datetime.utcnow().strftime("%H%M%S%f")
        stored_name = f"{file_id}.{ext}"

        save_path = save_dir / stored_name
        file_storage.save(save_path)

        # 更新 meta
        meta_path = self._meta_path(kb_name)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta["tmp"].append({
            "id": file_id,
            "filename": filename,
            "stored_name": stored_name,
            "path": str(save_path),
            "created_at": _now()
        })

        meta["updated_at"] = _now()

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta


# 单例实例（全局使用）
kb_service = KBService()