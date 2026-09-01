# backend/app/services/conversation_store.py
"""SQLite 对话账本 —— 标准库 sqlite3，零依赖。

设计要点：
- 单例（模块级 conversation_store）
- __init__ 只记 path，init_db() 一次性建表/索引 + 设 PRAGMA
- 每方法独立开连接（不缓存到模块级），避开 Flask reloader fork
- 软删：conversation.deleted_at，所有 SELECT 都带 deleted_at IS NULL
- 落库失败绝不抛给上层（store 内部 try/except 吞掉，由调用方自己判断）
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


SCHEMA_SQL: List[str] = [
    """
    CREATE TABLE IF NOT EXISTS conversation (
        id              TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL DEFAULT 'local',
        title           TEXT NOT NULL DEFAULT '',
        kb_id           TEXT,
        message_count   INTEGER NOT NULL DEFAULT 0,
        created_at      INTEGER NOT NULL,
        updated_at      INTEGER NOT NULL,
        deleted_at      INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS message (
        id              TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        user_id         TEXT NOT NULL DEFAULT 'local',
        role            TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
        content         TEXT NOT NULL DEFAULT '',
        status          TEXT NOT NULL DEFAULT 'complete'
                        CHECK (status IN ('streaming','complete','interrupted','error')),
        attachments     TEXT,
        ref_meta        TEXT,
        usage_json      TEXT,
        safety_json     TEXT,
        created_at      INTEGER NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversation(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS request_log (
        id              TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        message_id      TEXT,
        user_id         TEXT NOT NULL DEFAULT 'local',
        model           TEXT,
        prompt_name     TEXT,
        use_rag         INTEGER NOT NULL DEFAULT 0,
        kb_id           TEXT,
        stream          INTEGER NOT NULL DEFAULT 0,
        http_status     INTEGER,
        error           TEXT,
        duration_ms     INTEGER,
        created_at      INTEGER NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_conv_user_updated ON conversation(user_id, updated_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_msg_conv_created  ON message(conversation_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_reqlog_conv       ON request_log(conversation_id, created_at DESC);",
]


class ConversationStore:
    def __init__(self) -> None:
        self._db_path: Path = DB_PATH
        self._init_lock = threading.Lock()
        self._initialized = False

    # ---------------- 初始化 ----------------
    def init_db(self) -> None:
        with self._init_lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                # WAL 模式持久化在文件头，只设一次
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                cur = conn.execute("PRAGMA user_version;")
                current = cur.fetchone()[0] if cur else 0
                if current < SCHEMA_VERSION:
                    for stmt in SCHEMA_SQL:
                        conn.execute(stmt)
                    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
            self._initialized = True
            logger.info(f"[ConversationStore] DB ready at {self._db_path} (schema v{SCHEMA_VERSION})")

    def _connect(self) -> sqlite3.Connection:
        # isolation_level=None → 我们手动 BEGIN/COMMIT（与 `with conn:` 的自动事务一致）
        conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
            timeout=10.0,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    # ---------------- 工具 ----------------
    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex

    # ---------------- 会话 ----------------
    def upsert_conversation(
        self,
        conv_id: str,
        user_id: str = "local",
        title: str = "",
        kb_id: Optional[str] = None,
    ) -> str:
        now = int(time.time() * 1000)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM conversation WHERE id=? AND deleted_at IS NULL",
                (conv_id,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE conversation SET updated_at=? WHERE id=?",
                    (now, conv_id),
                )
                return conv_id
            conn.execute(
                """INSERT INTO conversation(id,user_id,title,kb_id,message_count,created_at,updated_at)
                   VALUES(?,?,?,?,0,?,?)""",
                (conv_id, user_id, title, kb_id, now, now),
            )
            return conv_id

    def get_or_create_for_user_message(
        self,
        conv_id: Optional[str],
        user_id: str = "local",
        title: str = "",
        kb_id: Optional[str] = None,
    ) -> Optional[str]:
        if not conv_id:
            return None
        return self.upsert_conversation(conv_id, user_id=user_id, title=title, kb_id=kb_id)

    def update_conversation_title(self, conv_id: str, title: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversation SET title=?, updated_at=? WHERE id=? AND deleted_at IS NULL",
                (title, int(time.time() * 1000), conv_id),
            )

    def list_conversations(self, user_id: str = "local", limit: int = 200) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id,user_id,title,kb_id,message_count,created_at,updated_at
                   FROM conversation
                   WHERE user_id=? AND deleted_at IS NULL
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id,user_id,title,kb_id,message_count,created_at,updated_at
                   FROM conversation WHERE id=? AND deleted_at IS NULL""",
                (conv_id,),
            ).fetchone()
        return dict(row) if row else None

    def soft_delete_conversation(self, conv_id: str) -> bool:
        now = int(time.time() * 1000)
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE conversation SET deleted_at=? WHERE id=? AND deleted_at IS NULL",
                (now, conv_id),
            )
            return cur.rowcount > 0

    # ---------------- 消息 ----------------
    def append_user_message(
        self,
        conv_id: str,
        content: str,
        attachments: Optional[List[str]] = None,
    ) -> str:
        msg_id = self.new_id()
        now = int(time.time() * 1000)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO message(id,conversation_id,user_id,role,content,status,
                   attachments,created_at)
                   VALUES(?,?,?,'user',?,'complete',?,?)""",
                (
                    msg_id, conv_id, "local", content,
                    json.dumps(attachments, ensure_ascii=False) if attachments else None,
                    now,
                ),
            )
            conn.execute(
                "UPDATE conversation SET message_count=message_count+1, updated_at=? WHERE id=?",
                (now, conv_id),
            )
        return msg_id

    def insert_assistant_placeholder(self, conv_id: str) -> str:
        msg_id = self.new_id()
        now = int(time.time() * 1000)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO message(id,conversation_id,user_id,role,content,status,created_at)
                   VALUES(?,?,?,'assistant','','streaming',?)""",
                (msg_id, conv_id, "local", now),
            )
            conn.execute(
                "UPDATE conversation SET message_count=message_count+1, updated_at=? WHERE id=?",
                (now, conv_id),
            )
        return msg_id

    def finalize_assistant(
        self,
        msg_id: str,
        content: str,
        status: str = "complete",
        references: Optional[List[dict]] = None,
        usage: Optional[dict] = None,
        safety: Optional[dict] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE message
                   SET content=?, status=?, ref_meta=?, usage_json=?, safety_json=?
                   WHERE id=?""",
                (
                    content, status,
                    json.dumps(references, ensure_ascii=False) if references else None,
                    json.dumps(usage, ensure_ascii=False) if usage else None,
                    json.dumps(safety, ensure_ascii=False) if safety else None,
                    msg_id,
                ),
            )

    def list_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id,conversation_id,user_id,role,content,status,
                          attachments,ref_meta,usage_json,safety_json,created_at
                   FROM message
                   WHERE conversation_id=?
                   ORDER BY created_at ASC, id ASC""",
                (conv_id,),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            for k in ("attachments", "ref_meta", "usage_json", "safety_json"):
                if d.get(k):
                    try:
                        d[k] = json.loads(d[k])
                    except Exception:
                        d[k] = None
            out.append(d)
        return out

    def get_message(self, msg_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM message WHERE id=?", (msg_id,)
            ).fetchone()
        return dict(row) if row else None


# 模块级单例
conversation_store = ConversationStore()
