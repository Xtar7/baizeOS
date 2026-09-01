# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS
from app.api import register_blueprints
from app.config.settings import PROJECT_ROOT

EMBEDDING_ROOT = PROJECT_ROOT / "models" / "embedding"

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
    from app.config.settings import DEBUG, ENV
    app.config['DEBUG'] = DEBUG
    app.config['ENV'] = 'development' if DEBUG else 'production'
    import os
    app.config['SECRET_KEY'] = os.getenv(
        'FLASK_SECRET_KEY',
        'dev-key-change-in-production'  # 仅开发环境
    )

    # =============================================
    # 跨域支持（前后端分离基本必备）
    # =============================================
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/v1/*": {"origins": "*"},  # 修正为实际路由前缀 /v1/
            # 生产环境建议改为：
            # r"/v1/*": {"origins": ["https://your-domain.com"]}
        },
    )

    # =============================================
    # 延迟导入并扫描 Embedding 模型（避免循环导入）
    # =============================================
    try:
        from app.services.embedding_factory import scan_embedding_models
        scan_embedding_models(EMBEDDING_ROOT)
        print("[启动] Embedding 模型扫描完成")
    except Exception as e:
        print(f"[警告] Embedding 模型扫描失败: {e}")

    # =============================================
    # 注册所有蓝图
    # =============================================
    register_blueprints(app)

    # =============================================
    # 初始化对话持久化（SQLite，标准库自带）
    # DB 坏掉不阻塞其他服务启动
    # =============================================
    try:
        from app.services.conversation_store import conversation_store
        conversation_store.init_db()
        print("[启动] 对话存储初始化完成")
    except Exception as e:
        print(f"[警告] 对话存储初始化失败: {e}")

    # 可选：提前加载 llm_service
    # try:
    #     from app.services.llm_service import llm_service
    #     _ = llm_service  # 触发加载
    # except Exception as e:
    #     print(f"[启动] LLM 初始化延迟加载: {e}")
    #
    return app