# app/api/__init__.py
import os
import importlib
import logging
from flask import Blueprint

logger = logging.getLogger(__name__)


def register_blueprints(app):
    """
    自动扫描 app/api/ 下所有子目录中的 .py 文件，
    并注册其中的 Blueprint
    """
    base_dir = os.path.dirname(__file__)
    registered_count = 0

    for subdir in os.listdir(base_dir):
        subdir_path = os.path.join(base_dir, subdir)

        # 只处理子目录
        if not os.path.isdir(subdir_path):
            continue

        # 必须是 python 包
        if not os.path.exists(os.path.join(subdir_path, "__init__.py")):
            continue

        for filename in os.listdir(subdir_path):
            if not filename.endswith(".py"):
                continue
            if filename == "__init__.py":
                continue

            module_name = f"app.api.{subdir}.{filename[:-3]}"

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