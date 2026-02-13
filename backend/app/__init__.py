# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS

from app.api import register_blueprints


def create_app(config=None):
    """
    Flask 应用工厂函数
    """
    app = Flask(
        __name__,
        instance_relative_config=False,
        # 如果项目有静态文件或模板，可根据实际目录调整路径
        # static_folder='../../static',
        # template_folder='../../templates',
    )

    # =============================================
    # 基本配置
    # =============================================
    app.config['ENV'] = 'development' if __debug__ else 'production'
    app.config['DEBUG'] = __debug__
    app.config['SECRET_KEY'] = 'your-secret-key-change-me'  # 生产环境请改成安全的随机值

    # =============================================
    # 跨域支持（前后端分离基本必备）
    # =============================================
    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": "*"}},  # 开发阶段可用 *，上线请收紧
    )

    # =============================================
    # 注册所有蓝图
    # =============================================
    register_blueprints(app)

    # 可选：提前加载 llm_service
    # try:
    #     from app.services.llm_service import llm_service
    #     _ = llm_service  # 触发加载
    # except Exception as e:
    #     print(f"[启动] LLM 初始化延迟加载: {e}")
    #
    return app