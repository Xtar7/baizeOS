# backend/tests/e2e_smoke.py
"""前后端联通性端到端冒烟测试。

直连 5000 端口跑一遍前端会走的每一条链路，输出 PASS/FAIL 汇总。
用法：
    backend/.venv/Scripts/python.exe tests/e2e_smoke.py [base_url]
默认 base_url = http://127.0.0.1:5000（走 Vite 代理时传 http://127.0.0.1:3000）
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def call(method: str, path: str, body=None, raw: bool = False):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = resp.read().decode("utf-8")
        return resp.status, (payload if raw else json.loads(payload))


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((PASS if ok else FAIL, name, detail))
    print(f"[{PASS if ok else FAIL}] {name}" + (f"  — {detail}" if detail else ""), flush=True)
    return ok


def main() -> int:
    # ---------- 1. 健康检查 ----------
    try:
        st, health = call("GET", "/v1/health")
        check("GET /v1/health", st == 200 and health.get("status") == "ok",
              f"llm.available={ (health.get('llm') or {}).get('available') }")
    except Exception as e:
        check("GET /v1/health", False, repr(e))
        return report()

    # ---------- 2. 模型列表 ----------
    try:
        st, models = call("GET", "/v1/models")
        check("GET /v1/models", st == 200 and isinstance(models.get("data"), list),
              f"{len(models.get('data', []))} 个模型, active={models.get('active')}")
    except Exception as e:
        check("GET /v1/models", False, repr(e))

    # ---------- 3. Embedding 模型列表 ----------
    try:
        st, emb = call("GET", "/v1/rag/embedding_models")
        check("GET /v1/rag/embedding_models", st == 200 and "models" in emb,
              f"default={emb.get('default')}")
    except Exception as e:
        check("GET /v1/rag/embedding_models", False, repr(e))

    # ---------- 4. 知识库列表 ----------
    kb_id = ""
    try:
        st, kbs = call("GET", "/v1/kb/list")
        data = kbs.get("data", [])
        kb_id = data[0]["kb_id"] if data else ""
        check("GET /v1/kb/list", st == 200 and isinstance(data, list), f"{len(data)} 个知识库")
    except Exception as e:
        check("GET /v1/kb/list", False, repr(e))

    if kb_id:
        try:
            st, kb = call("GET", f"/v1/kb/{kb_id}")
            check("GET /v1/kb/{id}", st == 200 and kb.get("kb_id") == kb_id,
                  f"files={len(kb.get('files', []))}")
        except Exception as e:
            check("GET /v1/kb/{id}", False, repr(e))

    # ---------- 5. 会话 CRUD ----------
    conv_id = ""
    try:
        st, conv = call("POST", "/v1/conversations", {"title": "e2e-smoke"})
        conv_id = conv.get("id", "")
        check("POST /v1/conversations", st == 201 and bool(conv_id), conv_id)
    except Exception as e:
        check("POST /v1/conversations", False, repr(e))

    if conv_id:
        try:
            st, patched = call("PATCH", f"/v1/conversations/{conv_id}", {"title": "e2e-renamed"})
            check("PATCH /v1/conversations/{id}", st == 200 and patched.get("title") == "e2e-renamed")
        except Exception as e:
            check("PATCH /v1/conversations/{id}", False, repr(e))

    # ---------- 6. 临时附件列表 ----------
    try:
        st, tmp = call("POST", "/v1/files/list", {"chat_id": conv_id or "probe"})
        check("POST /v1/files/list", st == 200 and "data" in tmp, f"total={tmp.get('total')}")
    except Exception as e:
        check("POST /v1/files/list", False, repr(e))

    # ---------- 7. 非流式对话 ----------
    if conv_id:
        try:
            t0 = time.time()
            st, res = call("POST", "/v1/chat/completions", {
                "model": "default", "stream": False, "conversation_id": conv_id,
                "messages": [{"role": "user", "content": "用一句话说明什么是向量数据库"}],
            })
            content = ""
            if st == 200:
                content = (res.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
            check("POST /v1/chat/completions (非流式)", st == 200 and bool(content),
                  f"{time.time() - t0:.1f}s, {len(content)} 字: {content[:40]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            check("POST /v1/chat/completions (非流式)", False, f"HTTP {e.code}: {body}")
        except Exception as e:
            check("POST /v1/chat/completions (非流式)", False, repr(e))

    # ---------- 8. 流式对话（前端 fetch + ReadableStream 路径） ----------
    if conv_id:
        try:
            t0 = time.time()
            req = urllib.request.Request(
                BASE + "/v1/chat/completions",
                data=json.dumps({
                    "model": "default", "stream": True, "conversation_id": conv_id,
                    "messages": [{"role": "user", "content": "用一句话解释什么是 RAG"}],
                }).encode(),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            deltas, done_frame, saw_done_sentinel, ctype = [], None, False, ""
            with urllib.request.urlopen(req, timeout=300) as resp:
                ctype = resp.headers.get("Content-Type", "")
                buf = b""
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n\n" in buf:
                        event, buf = buf.split(b"\n\n", 1)
                        for line in event.decode("utf-8", "replace").split("\n"):
                            if not line.startswith("data: "):
                                continue
                            data = line[6:].strip()
                            if data == "[DONE]":
                                saw_done_sentinel = True
                                continue
                            try:
                                obj = json.loads(data)
                            except Exception:
                                continue
                            if obj.get("done"):
                                done_frame = obj
                            elif obj.get("choices"):
                                text = (obj["choices"][0].get("delta") or {}).get("content")
                                if text:
                                    deltas.append(text)
            text = "".join(deltas)
            check("POST /v1/chat/completions (SSE 流式)",
                  bool(text) and "text/event-stream" in ctype and saw_done_sentinel,
                  f"{time.time() - t0:.1f}s, {len(text)} 字, done帧={'有' if done_frame else '无'}, "
                  f"sentinel={saw_done_sentinel}, ctype={ctype}")
            if done_frame:
                print(f"       usage={done_frame.get('usage')}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            check("POST /v1/chat/completions (SSE 流式)", False, f"HTTP {e.code}: {body}")
        except Exception as e:
            check("POST /v1/chat/completions (SSE 流式)", False, repr(e))

    # ---------- 9. 落库校验：字段契约必须与前端 ConversationMessage 对齐 ----------
    if conv_id:
        try:
            time.sleep(0.5)  # 给 finalize 落库留一点余量
            st, full = call("GET", f"/v1/conversations/{conv_id}?include_messages=true")
            msgs = full.get("messages", [])
            roles = [m["role"] for m in msgs]
            keys_ok = all(
                k in msgs[-1] for k in ("references", "usage", "safety", "status")
            ) if msgs else False
            check("GET /v1/conversations/{id}?include_messages=true",
                  st == 200 and len(msgs) >= 2 and keys_ok,
                  f"{len(msgs)} 条消息 roles={roles} 字段契约={'对' if keys_ok else '错'}")
            print(f"       末条 status={msgs[-1].get('status')!r} "
                  f"usage={msgs[-1].get('usage')}")
        except Exception as e:
            check("GET /v1/conversations/{id}?include_messages=true", False, repr(e))

    # ---------- 10. 会话列表已刷新 ----------
    if conv_id:
        try:
            st, lst = call("GET", "/v1/conversations?user_id=local")
            found = next((c for c in lst.get("data", []) if c["id"] == conv_id), None)
            check("会话出现在列表中", found is not None,
                  f"title={found.get('title')!r} message_count={found.get('message_count')}"
                  if found else "未找到")
        except Exception as e:
            check("会话出现在列表中", False, repr(e))

    # ---------- 11. 软删 ----------
    if conv_id:
        try:
            st, d = call("DELETE", f"/v1/conversations/{conv_id}")
            check("DELETE /v1/conversations/{id}", st == 200 and d.get("deleted") is True)
        except Exception as e:
            check("DELETE /v1/conversations/{id}", False, repr(e))

    # ---------- 12. 404 契约 ----------
    try:
        st, _ = call("GET", "/v1/conversations/does-not-exist")
        check("未知会话返回 404", st == 404, f"got {st}")
    except urllib.error.HTTPError as e:
        check("未知会话返回 404", e.code == 404, f"got {e.code}")

    # ---------- 13. 会话标题自动生成 / 手动改名不被覆盖 ----------
    # 前端会先建一条空会话，首条消息到达后才应补上标题。
    # 曾经因 upsert 只更新 updated_at 而漏写 title，导致侧边栏全是无名会话。
    conv_id = f"title-probe-{int(time.time() * 1000)}"
    try:
        call("POST", "/v1/conversations", {"conversation_id": conv_id})
        _, empty = call("GET", f"/v1/conversations/{conv_id}")
        check("新建会话标题初始为空", empty.get("title") == "", repr(empty.get("title")))

        # 发一条消息 → 标题应取自用户消息前 60 字
        call("POST", "/v1/chat/completions", {
            "model": "default",
            "messages": [{"role": "user", "content": "标题自动生成探针消息"}],
            "stream": False,
            "conversation_id": conv_id,
        })
        _, titled = call("GET", f"/v1/conversations/{conv_id}")
        auto_title = titled.get("title") or ""
        check("首条消息自动填充标题", bool(auto_title), f"title={auto_title[:24]!r}")

        # 手动改名 → 后续消息不得覆盖
        call("PATCH", f"/v1/conversations/{conv_id}", {"title": "manual-title-keep"})
        call("POST", "/v1/chat/completions", {
            "model": "default",
            "messages": [{"role": "user", "content": "第二条消息不应覆盖手动标题"}],
            "stream": False,
            "conversation_id": conv_id,
        })
        _, renamed = call("GET", f"/v1/conversations/{conv_id}")
        check("手动改名不被后续消息覆盖",
              renamed.get("title") == "manual-title-keep",
              f"title={renamed.get('title')!r}")
    except Exception as e:
        check("会话标题自动生成/手动改名", False, repr(e))
    finally:
        try:
            call("DELETE", f"/v1/conversations/{conv_id}")
        except Exception:
            pass

    return report()


def report() -> int:
    failed = [r for r in results if r[0] == FAIL]
    print("\n" + "=" * 52)
    print(f"  合计 {len(results)} 项，通过 {len(results) - len(failed)}，失败 {len(failed)}")
    if failed:
        for _, name, detail in failed:
            print(f"  ✗ {name}: {detail}")
    print("=" * 52)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())