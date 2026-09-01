# -*- coding: utf-8 -*-
"""
baizeOS 一键启动入口
====================
同时拉起 Flask 后端 (localhost:5000) 与 Vite 前端开发服务器 (localhost:3000)，
前端就绪后自动打开浏览器；Ctrl+C 一次性退出并清理两个子进程。

用法：
    python start.py          # 或双击 start.bat
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_URL = "http://localhost:5000"
FRONTEND_URL = "http://localhost:3000"

IS_WIN = sys.platform == "win32"


def info(msg: str) -> None:
    print(f"\033[36m[start]\033[0m {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"\033[33m[start]\033[0m {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"\033[31m[start]\033[0m {msg}", flush=True)


def port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_url(url: str, timeout: float = 60.0, expect_status: int = 200) -> bool:
    """轮询直到 URL 返回 expect_status（默认 200）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status == expect_status:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError, ValueError):
            time.sleep(0.6)
    return False


def kill_tree(pid: int) -> None:
    """连同子进程树一起结束（Windows 下 vite/flask 都可能有子进程）。"""
    if not pid:
        return
    try:
        if IS_WIN:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
            )
        else:
            subprocess.run(["kill", "--", "-" + str(pid)], capture_output=True)
    except OSError:
        pass


def run_step(cmd: list[str], cwd: Path, what: str) -> None:
    """前台跑一个准备步骤（如安装依赖），输出实时透传。"""
    info(f"{what} …")
    proc = subprocess.run(cmd, cwd=cwd)
    if proc.returncode != 0:
        fail(f"{what} 失败（退出码 {proc.returncode}）")
        sys.exit(proc.returncode)


def main() -> int:
    # Windows 控制台默认 GBK，强制 UTF-8 避免中文乱码
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 56)
    print("  baizeOS · 本地知识库问答系统")
    print("  后端 http://localhost:5000   前端 http://localhost:3000")
    print("=" * 56)

    if not BACKEND_DIR.exists() or not FRONTEND_DIR.exists():
        fail("目录不完整：需要与 start.py 同级的 backend/ 与 frontend/")
        return 1

    pnpm = shutil.which("pnpm")
    if not pnpm:
        warn("未找到 pnpm，回退使用 npm（建议：npm i -g pnpm）")
        pnpm = shutil.which("npm")
        if not pnpm:
            fail("未找到 npm/pnpm，请先安装 Node.js：https://nodejs.org/")
            return 1
    # ---- 前端依赖 ----
    if not (FRONTEND_DIR / "node_modules").exists():
        run_step([pnpm, "install"], FRONTEND_DIR, "首次运行，安装前端依赖")

    procs: dict[str, subprocess.Popen] = {}
    restarted: set[str] = set()  # 已为该角色使用过"自动重启一次"名额

    try:
        # ---- 后端（直接调用 venv 内的 Python，避免系统默认 Python 找不到依赖） ----
        if port_busy(5000):
            warn("端口 5000 已被占用：假定后端已在运行，等待 /v1/health 就绪 …")
        else:
            info("启动后端 Flask …")
            backend_py = BACKEND_DIR / ".venv" / "Scripts" / "python.exe" if IS_WIN else BACKEND_DIR / ".venv" / "bin" / "python"
            if not backend_py.exists():
                fail(f"未找到后端虚拟环境：{backend_py}")
                return 1
            procs["backend"] = subprocess.Popen(
                [str(backend_py), "app.py"],
                cwd=BACKEND_DIR,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

        # ---- 等后端就绪（先后端、再前端、再开浏览器，避开启动竞态） ----
        if not wait_url(BACKEND_URL + "/v1/health", timeout=90.0, expect_status=200):
            fail("后端 90 秒内未就绪（/v1/health 未返回 200）")
            for p in procs.values():
                kill_tree(p.pid)
            return 1
        info("后端就绪：/v1/health → 200")

        # ---- 前端 ----
        if port_busy(3000):
            warn("端口 3000 已被占用：Vite 将自动换端口，注意控制台提示。")
        info("启动前端 Vite …")
        procs["frontend"] = subprocess.Popen([pnpm, "run", "dev"], cwd=FRONTEND_DIR)

        # ---- 等前端就绪并打开浏览器 ----
        if wait_url(FRONTEND_URL, timeout=60.0):
            info(f"前端就绪，打开浏览器：{FRONTEND_URL}")
            webbrowser.open(FRONTEND_URL)
        else:
            warn("60 秒内未检测到前端就绪（首次启动编译可能较慢），可手动访问 " + FRONTEND_URL)

        info("两个服务运行中，按 Ctrl+C 一起退出。")

        # ---- 守护循环：后端崩联动关前端；前端崩自动重启一次 ----
        while True:
            time.sleep(2)

            # 1) 后端是前端数据来源，后端挂了就别挣扎，联动关闭前端
            backend = procs.get("backend")
            if backend and backend.poll() is not None:
                code = backend.returncode
                fail(f"后端退出（码 {code}），联动关闭前端后退出。")
                frontend = procs.get("frontend")
                if frontend and frontend.poll() is None:
                    kill_tree(frontend.pid)
                return code or 1

            # 2) 前端崩了允许自动重启一次（Vite/HMR 偶发退出后能自愈）
            frontend = procs.get("frontend")
            if frontend and frontend.poll() is not None:
                code = frontend.returncode
                if "frontend" in restarted:
                    fail(f"前端再次退出（码 {code}），已达到自动重启上限，整体关闭。")
                    return code or 1
                warn(f"前端退出（码 {code}），尝试自动重启一次 …")
                restarted.add("frontend")
                procs["frontend"] = subprocess.Popen(
                    [pnpm, "run", "dev"], cwd=FRONTEND_DIR
                )
    except KeyboardInterrupt:
        print(flush=True)
        info("正在退出 …")
        return 0
    finally:
        for p in procs.values():
            kill_tree(p.pid)


if __name__ == "__main__":
    sys.exit(main())
