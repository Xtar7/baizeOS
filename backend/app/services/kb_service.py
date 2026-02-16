# backend/app/services/kb_service.py
import json
import mimetypes
import shutil
from pathlib import Path
from datetime import datetime
import time
import uuid  # 用于随机部分

from app.config.settings import PROJECT_ROOT

KB_ROOT = PROJECT_ROOT / "knowledge_base"


def _now():
    return datetime.utcnow().isoformat()


class KBService:
    def __init__(self):
        # 确保 knowledge_base 目录存在
        KB_ROOT.mkdir(parents=True, exist_ok=True)

    def _generate_uuid_v7(self) -> str:
        """
        生成 UUID v7（时间有序 + 随机）
        - 前48位：毫秒级 Unix 时间戳
        - 版本位：0111 (v7)
        - 变体位：10xx (RFC 4122)
        - 剩余随机位
        """
        # Unix 时间戳（毫秒）
        timestamp_ms = int(time.time() * 1000)
        ts_bytes = timestamp_ms.to_bytes(6, 'big')

        # 随机字节（从 uuid4 取）
        rand_bytes = uuid.uuid4().bytes

        # 构造 16 字节 UUID
        uuid_bytes = bytearray(16)
        uuid_bytes[0:6] = ts_bytes
        # 第7字节：版本 7 (0b0111xxxx)
        uuid_bytes[6] = 0x70 | (rand_bytes[0] & 0x0f)
        # 字节7-9：随机 (24 位)
        uuid_bytes[7:10] = rand_bytes[1:4]
        # 第11字节：变体 0b10xxxxxx
        uuid_bytes[10] = 0x80 | (rand_bytes[4] & 0x3f)
        # 剩余字节：随机 (40 位)
        uuid_bytes[11:16] = rand_bytes[5:10]

        return str(uuid.UUID(bytes=bytes(uuid_bytes)))

    def _kb_path(self, kb_id: str) -> Path:
        """知识库文件夹路径：直接用 kb_id (UUID)"""
        return KB_ROOT / kb_id

    def _meta_path(self, kb_id: str) -> Path:
        """meta.json 路径"""
        return self._kb_path(kb_id) / "kb_meta.json"

    # -----------------------------
    # 创建知识库
    # -----------------------------
    def create(self, display_name: str, system_prompt: str = "", description: str = ""):
        """
        创建 KB：生成 UUID id，display_name 是用户可见名字
        """
        if not display_name or not display_name.strip():
            raise ValueError("知识库名称不能为空")

        kb_id = self._generate_uuid_v7()
        kb_path = self._kb_path(kb_id)

        if kb_path.exists():
            # UUID 冲突概率极低，理论上不会发生
            raise ValueError("知识库已存在")

        # 创建目录结构
        (kb_path / "files").mkdir(parents=True)
        (kb_path / "vector_store").mkdir()

        meta = {
            "id": kb_id,
            "display_name": display_name.strip(),
            "description": description,
            "system_prompt": system_prompt,
            "created_at": _now(),
            "updated_at": _now(),
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
    # 删除 KB（用 UUID id）
    # -----------------------------
    def delete(self, kb_id: str):
        kb_path = self._kb_path(kb_id)
        if kb_path.exists():
            shutil.rmtree(kb_path)
            return True
        return False

    # -----------------------------
    # 重命名 KB（只改 display_name）
    # -----------------------------
    def rename(self, kb_id: str, new_display_name: str):
        """
        重命名：只修改 meta.display_name，不动文件夹、文件或向量存储
        """
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
    # 更新 system_prompt
    # -----------------------------
    def update_prompt(self, kb_id: str, system_prompt: str):
        meta_path = self._meta_path(kb_id)
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
    def save_file(self, kb_id: str, file_storage):
        kb_path = self._kb_path(kb_id)
        if not kb_path.exists():
            raise ValueError(f"知识库不存在: {kb_id}")

        filename = file_storage.filename
        if not filename:
            raise ValueError("文件名为空")

        ext = Path(filename).suffix.lower().lstrip(".")
        if not ext:
            raise ValueError("文件缺少扩展名")

        date_str = datetime.utcnow().strftime("%Y-%m-%d")

        save_dir = kb_path / "files" / date_str / ext
        save_dir.mkdir(parents=True, exist_ok=True)

        file_id = datetime.utcnow().strftime("%H%M%S%f")
        stored_name = f"{file_id}.{ext}"

        save_path = save_dir / stored_name

        try:
            file_storage.save(save_path)
        except Exception as e:
            raise RuntimeError(f"文件保存失败: {str(e)}")

        # 更新 meta
        meta_path = self._meta_path(kb_id)
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            raise RuntimeError(f"读取 meta 失败: {str(e)}")

        meta["files"].append({
            "id": file_id,
            "filename": filename,
            "stored_name": stored_name,
            "path": str(save_path),
            "created_at": _now(),
            "size": save_path.stat().st_size,  # 新增：记录文件大小
            "mime_type": mimetypes.guess_type(str(save_path))[0]  # 新增：MIME
        })

        meta["updated_at"] = _now()

        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            save_path.unlink(missing_ok=True)  # 失败时删除已保存的文件
            raise RuntimeError(f"更新 meta 失败: {str(e)}")

        return meta



# 单例实例（全局使用）
kb_service = KBService()