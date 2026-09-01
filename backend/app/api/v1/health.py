# backend/app/api/v1/health.py
"""轻量健康检查 —— 不触发 LLM/Embedding 加载。

约定：5000 端口一旦 listen，此端点立即返回 200。
由 start.py 用作后端就绪判定；由 Vite 代理作为转发健康前提。
"""
import time
from flask import Blueprint, jsonify

from app.config.settings import ENV, DEBUG, SERVER_PORT

health_bp = Blueprint("health", __name__, url_prefix="/v1")


@health_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "baizeos-backend",
        "env": ENV,
        "debug": DEBUG,
        "port": SERVER_PORT,
        "pid": None,
        "uptime_s": None,
        "ts": time.time(),
    }), 200
