# backend/tests/e2e_write_paths.py
"""写路径端到端测试：知识库 CRUD + 临时文件上传/删除。

与 e2e_smoke.py 互补 —— 那边只读 + 会话，这边跑会改动数据的接口。
全程只用临时创建的资源，结束时清理，不碰用户已有数据。

用法：
    backend/.venv/Scripts/python.exe tests/e2e_write_paths.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []
created_kbs: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((PASS if ok else FAIL, name, detail))
    print(f"[{PASS if ok else FAIL}] {name}" + (f"  — {detail}" if detail else ""), flush=True)
    return ok


def req(method: str, path: str, body=None, raw_body: bytes | None = None,
        content_type: str | None = None):
    url = BASE + path
    data = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(url, data=data, method=method)
    if content_type:
        r.add_header("Content-Type", content_type)
    elif data:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=300) as resp:
        return resp.status, json.loads(resp.read() or b"{}")


def multipart(fields: dict[str, str], file_field: str, filename: str, content: bytes):
    boundary = "----baizeos" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n'.encode()
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def main() -> int:
    # ---------- 知识库 CRUD ----------
    kb_id = ""
    name = f"e2e-write-{uuid.uuid4().hex[:8]}"
    try:
        st, kb = req("POST", "/v1/kb", {"display_name": name, "description": "写路径测试"})
        kb_id = kb.get("kb_id", "")
        created_kbs.append(kb_id)
        check("POST /v1/kb", st in (200, 201) and bool(kb_id), f"{kb_id}")
    except urllib.error.HTTPError as e:
        check("POST /v1/kb", False, f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:160]}")
    except Exception as e:
        check("POST /v1/kb", False, repr(e))

    if kb_id:
        try:
            st, kb = req("GET", f"/v1/kb/{kb_id}")
            check("GET /v1/kb/{id}", st == 200 and kb.get("display_name") == name,
                  f"files={len(kb.get('files', []))}")
        except Exception as e:
            check("GET /v1/kb/{id}", False, repr(e))

        try:
            st, up = req("PUT", f"/v1/kb/{kb_id}",
                         {"display_name": name + "-改", "description": "改过"})
            got = up.get("kb", up)
            check("PUT /v1/kb/{id}", st == 200 and got.get("display_name") == name + "-改",
                  f"updated={up.get('updated')} needs_rebuild={up.get('needs_rebuild')}")
        except urllib.error.HTTPError as e:
            check("PUT /v1/kb/{id}", False, f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:160]}")
        except Exception as e:
            check("PUT /v1/kb/{id}", False, repr(e))

        # 上传文件（字段名必须是 file）
        try:
            body, ct = multipart({"kb_id": kb_id}, "file", "e2e.txt",
                                 "baizeOS 写路径冒烟测试文档。\n".encode())
            st, up = req("POST", "/v1/kb/upload", raw_body=body, content_type=ct)
            fi = up.get("file_info", {})
            check("POST /v1/kb/upload (multipart, 字段名 file)", st in (200, 201) and bool(fi.get("kb_file_id")),
                  f"kb_file_id={fi.get('kb_file_id')} bytes={fi.get('bytes')}")
        except urllib.error.HTTPError as e:
            check("POST /v1/kb/upload (multipart, 字段名 file)", False,
                  f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:200]}")
        except Exception as e:
            check("POST /v1/kb/upload (multipart, 字段名 file)", False, repr(e))

        # 详情应能看到刚上传的文件
        try:
            st, kb = req("GET", f"/v1/kb/{kb_id}")
            n = len(kb.get("files", []))
            check("上传后详情含 files", st == 200 and n >= 1, f"files={n}")
        except Exception as e:
            check("上传后详情含 files", False, repr(e))

        try:
            st, d = req("DELETE", "/v1/kb", {"kb_id": kb_id})
            ok = st == 200 and (d.get("deleted") is True or d.get("deleted_count", 0) >= 1)
            check("DELETE /v1/kb (body 传 kb_id)", ok, f"deleted_count={d.get('deleted_count')}")
            if ok:
                created_kbs.remove(kb_id)
        except urllib.error.HTTPError as e:
            check("DELETE /v1/kb (body 传 kb_id)", False, f"HTTP {e.code}")
        except Exception as e:
            check("DELETE /v1/kb (body 传 kb_id)", False, repr(e))

    # ---------- 临时文件（聊天附件） ----------
    chat_id = uuid.uuid4().hex
    tmp_id = ""
    try:
        body, ct = multipart({"chat_id": chat_id}, "file", "note.txt", b"hello attach")
        st, up = req("POST", "/v1/files/upload", raw_body=body, content_type=ct)
        tmp_id = (up.get("file") or {}).get("tmp_file_id", "")
        check("POST /v1/files/upload", st in (200, 201) and bool(tmp_id), f"tmp_file_id={tmp_id}")
    except urllib.error.HTTPError as e:
        check("POST /v1/files/upload", False, f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:160]}")
    except Exception as e:
        check("POST /v1/files/upload", False, repr(e))

    try:
        st, lst = req("POST", "/v1/files/list", {"chat_id": chat_id})
        data = lst.get("data", [])
        check("POST /v1/files/list", st == 200 and any(
            f.get("tmp_file_id") == tmp_id for f in data), f"total={lst.get('total')}")
    except Exception as e:
        check("POST /v1/files/list", False, repr(e))

    if tmp_id:
        try:
            st, d = req("POST", "/v1/files/delete", {"chat_id": chat_id, "tmp_file_id": tmp_id})
            check("POST /v1/files/delete", st == 200 and d.get("deleted_count", 0) >= 1,
                  f"deleted_count={d.get('deleted_count')}")
        except Exception as e:
            check("POST /v1/files/delete", False, repr(e))

    # ---------- 清理兜底 ----------
    for leftover in created_kbs:
        try:
            req("DELETE", "/v1/kb", {"kb_id": leftover})
        except Exception:
            pass
    if created_kbs:
        print(f"[warn] 清理失败，残留知识库: {created_kbs}")

    failed = [r for r in results if r[0] == FAIL]
    print("\n" + "=" * 52)
    print(f"  合计 {len(results)} 项，通过 {len(results) - len(failed)}，失败 {len(failed)}")
    for _, name_, detail in failed:
        print(f"  ✗ {name_}: {detail}")
    print("=" * 52)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())