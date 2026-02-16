# backend/app/api/__init__.py
import os
import importlib
import logging
from flask import Blueprint

logger = logging.getLogger(__name__)


def register_blueprints(app):
    """
    递归扫描 app/api/ 下所有子目录中的 .py 文件，
    自动注册其中的 Blueprint
    """
    base_dir = os.path.dirname(__file__)
    registered_count = 0

    for root, dirs, files in os.walk(base_dir):

        # 只处理 python 包目录
        if "__init__.py" not in files:
            continue

        # 计算模块路径
        rel_path = os.path.relpath(root, base_dir)
        if rel_path == ".":
            package = "app.api"
        else:
            package = "app.api." + rel_path.replace(os.sep, ".")

        for filename in files:
            if not filename.endswith(".py"):
                continue
            if filename == "__init__.py":
                continue

            module_name = f"{package}.{filename[:-3]}"

            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                logger.warning(f"导入模块失败 {module_name}: {e}")
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if not isinstance(obj, Blueprint):
                    continue

                if obj.name in app.blueprints:
                    logger.warning(f"蓝图 {obj.name} 已注册，跳过")
                    continue

                app.register_blueprint(obj)
                registered_count += 1
                logger.info(f"[API] 注册蓝图: {obj.name} ← {module_name}")

    if registered_count == 0:
        logger.warning("没有发现任何蓝图")