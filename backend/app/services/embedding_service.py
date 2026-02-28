# app/services/embedding_service.py
# 只保留兼容性代理，未来可以逐步迁移掉

from app.services.embedding_factory import (
    scan_embedding_models,
    get_available_embedding_models,
    get_embedding_service,
)

# 导出相同的接口，保持兼容
__all__ = [
    "scan_embedding_models",
    "get_available_embedding_models",
    "get_embedding_service",
]