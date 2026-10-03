# backend/app/api/v1/health.py
"""轻量健康检查 —— 不触发 LLM/Embedding 加载。

约定：5000 端口一旦 listen，此端点立即返回 200。
由 start.py 用作后端就绪判定；由 Vite 代理作为转发健康前提。

注意：这里刻意不 import llm_service —— 健康检查必须在任何模型加载
失败的情况下也能立刻返回，否则 start.py 永远等不到就绪。
"""
import time
from flask import Blueprint, jsonify

from app.config.settings import ENV, DEBUG, SERVER_PORT

health_bp = Blueprint("health", __name__, url_prefix="/v1")


@health_bp.route("/health", methods=["GET"])
def health():
    # LLM 状态走懒加载快照：模块已经因为别的原因被 import 过就复用，
    # 否则完全不碰（避免健康检查触发几秒的模型扫描）。
    llm_info = None
    try:
        import sys

        mod = sys.modules.get("app.services.llm_service")
        if mod is not None:
            llm_info = mod.llm_service.status()
    except Exception:
        llm_info = {"available": False, "error": "llm_service 未初始化"}

    return jsonify({
        "status": "ok",
        "service": "baizeos-backend",
        "env": ENV,
        "debug": DEBUG,
        "port": SERVER_PORT,
        "pid": None,
        "uptime_s": None,
        "ts": time.time(),
        "llm": llm_info,
    }), 200
