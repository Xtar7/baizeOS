# backend/app/utils/json_provider.py
import json
import numpy as np
from flask.json.provider import DefaultJSONProvider


class NumpyJSONProvider(DefaultJSONProvider):
    """
    企业级 JSON 序列化器
    自动支持：
    - numpy.float32 / float64 / float16
    - numpy.int32 / int64
    - numpy.ndarray
    - faiss float32
    - 其他数值类型
    """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, (np.floating, np.float32, np.float64, np.float16)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        type_name = type(obj).__name__
        if type_name in ('float32', 'float64', 'float16', 'int32', 'int64'):
            return float(obj) if 'float' in type_name else int(obj)
        if hasattr(obj, '__module__') and hasattr(obj, '__class__'):
            module_name = getattr(obj.__class__, '__module__', '')
            if module_name.startswith('numpy') or module_name.startswith('faiss'):
                if hasattr(obj, 'item'):
                    return obj.item()
                if hasattr(obj, '__float__'):
                    return float(obj)
                if hasattr(obj, '__int__'):
                    return int(obj)
        return super().default(obj)