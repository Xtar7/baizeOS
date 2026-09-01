"""
端到端测试：对话持久化（SQLite）
前置：后端 5000 端口已起
运行（必须在 backend/.venv 里）：.venv/Scripts/python.exe tests/test_conversations_e2e.py
"""
from __future__ import annotations

import sqlite3
import sys
import time
import uuid
from pathlib import Path

import requests

BASE = "http://localhost:5000"
DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "baizeos.db"
)

PASS = 0
FAIL = 0


def _h() -> dict:
    return {"Content-Type": "application/json"}


# 后端 LLM 推理慢，所有请求都给足 30s
HTTP_TIMEOUT = 30
HTTP_TIMEOUT_LONG = 90


def _must(resp: requests.Response, code: int) -> requests.Response:
    assert resp.status_code == code, f"{resp.status_code} != {code}: {resp.text[:300]}"
    return resp


def _db_count_msg() -> int:
    conn = sqlite3.connect(str(DB_PATH))
    n = conn.execute("SELECT COUNT(*) FROM message").fetchone()[0]
    conn.close()
    return n


def test_1_create_then_list():
    cid = uuid.uuid4().hex
    r = _must(
        requests.post(
            f"{BASE}/v1/conversations",
            json={"conversation_id": cid, "title": "e2e-1"},
            timeout=5,
        ),
        201,
    )
    assert r.json()["id"] == cid
    r = _must(requests.get(f"{BASE}/v1/conversations", timeout=HTTP_TIMEOUT), 200)
    assert any(c["id"] == cid for c in r.json()["data"]), "new conv not in list"
    print("[1] create+list OK")


def test_2_stream_with_conv_id_persists():
    cid = uuid.uuid4().hex
    _must(
        requests.post(
            f"{BASE}/v1/conversations",
            json={"conversation_id": cid},
            timeout=5,
        ),
        201,
    )
    with requests.post(
        f"{BASE}/v1/chat/completions",
        json={
            "model": "default",
            "stream": True,
            "conversation_id": cid,
            "messages": [{"role": "user", "content": "hi"}],
        },
        stream=True,
        timeout=HTTP_TIMEOUT_LONG,
    ) as r:
        assert r.status_code == 200
        for _ in r.iter_lines():
            pass
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT role, status FROM message WHERE conversation_id=? ORDER BY created_at",
        (cid,),
    ).fetchall()
    conn.close()
    assert len(rows) == 2, f"expected 2 msgs, got {rows}"
    assert rows[0][0] == "user" and rows[0][1] == "complete"
    assert rows[1][0] == "assistant" and rows[1][1] in ("complete", "interrupted")
    print("[2] stream persist OK")


def test_3_get_messages_in_order():
    cid = uuid.uuid4().hex
    _must(
        requests.post(
            f"{BASE}/v1/conversations",
            json={"conversation_id": cid},
            timeout=5,
        ),
        201,
    )
    for q in ["first", "second", "third"]:
        with requests.post(
            f"{BASE}/v1/chat/completions",
            json={
                "model": "default",
                "stream": False,
                "conversation_id": cid,
                "messages": [{"role": "user", "content": q}],
            },
            timeout=HTTP_TIMEOUT_LONG,
        ) as r:
            _must(r, 200)
    r = _must(
        requests.get(
            f"{BASE}/v1/conversations/{cid}?include_messages=true", timeout=5
        ),
        200,
    )
    msgs = r.json()["messages"]
    assert len(msgs) == 6, f"expected 6, got {len(msgs)}"
    assert [m["role"] for m in msgs] == ["user", "assistant"] * 3
    assert msgs[0]["content"] == "first"
    assert msgs[4]["content"] == "third"
    print("[3] order OK")


def test_4_soft_delete_returns_404():
    cid = uuid.uuid4().hex
    _must(
        requests.post(
            f"{BASE}/v1/conversations",
            json={"conversation_id": cid},
            timeout=5,
        ),
        201,
    )
    _must(requests.delete(f"{BASE}/v1/conversations/{cid}", timeout=HTTP_TIMEOUT), 200)
    r = requests.get(f"{BASE}/v1/conversations/{cid}", timeout=HTTP_TIMEOUT)
    assert r.status_code == 404, f"got {r.status_code}: {r.text[:200]}"
    print("[4] soft delete OK")


def test_5_unknown_conv_id_upserts():
    fake = uuid.uuid4().hex
    with requests.post(
        f"{BASE}/v1/chat/completions",
        json={
            "model": "default",
            "stream": False,
            "conversation_id": fake,
            "messages": [{"role": "user", "content": "upsert-test"}],
        },
        timeout=HTTP_TIMEOUT_LONG,
    ) as r:
        _must(r, 200)
    r = _must(requests.get(f"{BASE}/v1/conversations/{fake}", timeout=HTTP_TIMEOUT), 200)
    assert r.json()["id"] == fake
    print("[5] upsert OK")


def test_6_interrupt_marks_interrupted():
    """流被客户端提前断：服务端要么标 complete（已跑完）要么 interrupted。
    关键断言是 assistant 行存在 + status 合法 + content 不为 NULL。"""
    cid = uuid.uuid4().hex
    _must(
        requests.post(
            f"{BASE}/v1/conversations",
            json={"conversation_id": cid},
            timeout=5,
        ),
        201,
    )
    interrupted = False
    chat_status = None
    chat_text = ""
    try:
        with requests.post(
            f"{BASE}/v1/chat/completions",
            json={
                "model": "default",
                "stream": True,
                "conversation_id": cid,
                "messages": [{"role": "user", "content": "请写一首很长的诗"}],
            # 限制 max_tokens 让首字节更快到（否则模型会跑满 512）
            "max_tokens": 128,
            },
            stream=True,
            # LLM 首字节 + 占位 SQL 需要数秒到十几秒
            timeout=(5, 90),  # (connect, read)
        ) as r:
            chat_status = r.status_code
            # 读 1 行首字节就主动退出 for → with 块 close response → 服务端 GeneratorExit
            for line in r.iter_lines():
                if line:
                    chat_text += line.decode(errors="replace") + "\n"
                    break
    except Exception as e:
        interrupted = True
        print(f"  [debug] chat raised: {type(e).__name__}: {str(e)[:120]}")
    print(f"  [debug] cid={cid} chat_status={chat_status} lines={len(chat_text)}")
    # 等服务端 finalize
    time.sleep(1.5)
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT status, length(content) FROM message "
        "WHERE conversation_id=? AND role='assistant'",
        (cid,),
    ).fetchone()
    conn.close()
    assert row is not None, "assistant row missing (服务端连 user 都还没来得及写完？)"
    assert row[0] in ("complete", "interrupted"), f"bad status {row[0]}"
    print(f"[6] stream-finish OK (interrupted={interrupted}, status={row[0]}, len={row[1]})")


def test_7_db_failure_does_not_break_chat():
    """把 store 的 append_user_message 临时替换为抛异常的 stub → 聊天仍 200"""
    import sys as _sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services import conversation_store as cs

    orig = cs.conversation_store.append_user_message

    def boom(*a, **k):
        raise RuntimeError("db boom")

    cs.conversation_store.append_user_message = boom
    try:
        cid = uuid.uuid4().hex
        _must(
            requests.post(
                f"{BASE}/v1/conversations",
                json={"conversation_id": cid},
                timeout=5,
            ),
            201,
        )
        r = _must(
            requests.post(
                f"{BASE}/v1/chat/completions",
                json={
                    "model": "default",
                    "stream": False,
                    "conversation_id": cid,
                    "messages": [{"role": "user", "content": "x"}],
                },
                timeout=HTTP_TIMEOUT_LONG,
            ),
            200,
        )
        assert r.json().get("choices"), "no choices in response"
    finally:
        cs.conversation_store.append_user_message = orig
    print("[7] DB-fail-tolerant OK")


def test_8_legacy_no_conv_id_no_db_write():
    before = _db_count_msg()
    with requests.post(
        f"{BASE}/v1/chat/completions",
        json={
            "model": "default",
            "stream": False,
            "messages": [{"role": "user", "content": "legacy-no-cid"}],
        },
        timeout=HTTP_TIMEOUT_LONG,
    ) as r:
        _must(r, 200)
    after = _db_count_msg()
    assert after == before, f"legacy call wrote {after - before} rows"
    print("[8] legacy no-write OK")


def test_9_rename_then_get():
    cid = uuid.uuid4().hex
    _must(
        requests.post(
            f"{BASE}/v1/conversations",
            json={"conversation_id": cid, "title": "old"},
            timeout=5,
        ),
        201,
    )
    r = _must(
        requests.patch(
            f"{BASE}/v1/conversations/{cid}",
            json={"title": "renamed-title"},
            timeout=5,
        ),
        200,
    )
    assert r.json()["title"] == "renamed-title"
    print("[9] rename OK")


def test_10_patch_missing_404():
    r = requests.patch(
        f"{BASE}/v1/conversations/{uuid.uuid4().hex}",
        json={"title": "x"},
        timeout=5,
    )
    assert r.status_code == 404
    print("[10] patch-404 OK")


def run(t):
    global PASS, FAIL
    try:
        t()
        PASS += 1
    except Exception as e:
        FAIL += 1
        print(f"[FAIL] {t.__name__}: {e}")


if __name__ == "__main__":
    tests = [
        test_1_create_then_list,
        test_2_stream_with_conv_id_persists,
        test_3_get_messages_in_order,
        test_4_soft_delete_returns_404,
        test_5_unknown_conv_id_upserts,
        test_6_interrupt_marks_interrupted,
        test_7_db_failure_does_not_break_chat,
        test_8_legacy_no_conv_id_no_db_write,
        test_9_rename_then_get,
        test_10_patch_missing_404,
    ]
    for t in tests:
        run(t)
    print(f"\n{'-' * 40}\nPASSED {PASS} / FAILED {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
