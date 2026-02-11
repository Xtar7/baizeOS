# backend/app/api/__init__.py
import os
import importlib
import logging
from flask import Blueprint

logger = logging.getLogger(__name__)


def register_blueprints(app):
    """
    自动扫描当前目录（backend/app/api/）下所有 .py 文件，并注册其中的 Blueprint
    """
    api_dir = os.path.dirname(__file__)
    registered_count = 0

    for filename in sorted(os.listdir(api_dir)):
        if not filename.endswith(".py"):
            continue
        if filename in ("__init__.py", "base.py"):
            continue

        # 改成 backend.app.api.xxx
        module_name = f"app.api.{filename[:-3]}"

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
                logger.warning(f"蓝图 {obj.name} 已注册，跳过: {module_name}")
                continue

            app.register_blueprint(obj)
            registered_count += 1
            logger.debug(f"已注册蓝图: {obj.name} ← {module_name}")

    if registered_count == 0:
        logger.warning("没有发现任何蓝图（app/api/ 目录下）")
    else:
        logger.info(f"成功自动注册 {registered_count} 个蓝图")