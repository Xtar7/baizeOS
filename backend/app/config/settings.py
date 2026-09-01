# backend/config/settings.py
from pathlib import Path
import os

# =============================================
# 基础路径（最重要部分，已根据你的描述调整）
# =============================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent   # → E:\baizeOS

BACKEND_DIR    = PROJECT_ROOT / "backend"
MODEL_DIR      = PROJECT_ROOT / "models"
LLM_SCAN_PATH  = MODEL_DIR / "llm"
KB_ROOT        = PROJECT_ROOT / "KB"              # 知识库根目录（唯一来源）
LOG_DIR        = PROJECT_ROOT / "logs"
DATA_DIR       = BACKEND_DIR / "data"
DB_PATH        = DATA_DIR / "baizeos.db"          # SQLite 对话账本（标准库自带）
# 测试data文件夹问题
# print("settings.py 位置:", Path(__file__).resolve())
# print("计算出的 PROJECT_ROOT:", PROJECT_ROOT)
# print("backend 是否存在:", (PROJECT_ROOT / "backend").exists())
# print("data 是否存在:", (PROJECT_ROOT / "backend" / "data").exists())

# 测试config配置问题
# print("[CONFIG] PROJECT_ROOT   :", PROJECT_ROOT)
# print("[CONFIG] MODEL_DIR      :", MODEL_DIR)
# print("[CONFIG] LLM_SCAN_PATH  :", LLM_SCAN_PATH)
# print("[CONFIG] LLM目录是否存在:", LLM_SCAN_PATH.exists())
# print("[CONFIG] LLM目录下文件  :", [f.name for f in LLM_SCAN_PATH.glob("*.gguf")] if LLM_SCAN_PATH.exists() else "不存在")
# =============================================
# 运行环境
# =============================================
ENV = os.getenv("APP_ENV", "prod")               # dev / test / prod
DEBUG = os.getenv("FLASK_DEBUG", "0" if ENV in ("dev", "test") else "0") == "1"

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000   # flask默认5000

# =============================================
# 日志
# =============================================
LOG_LEVEL = "INFO" if not DEBUG else "DEBUG"
LOG_BACKEND_DIR = LOG_DIR / "backend"
LOG_RAG_DIR = LOG_DIR / "rag"

# =============================================
# LLM 配置
# =============================================
LLM_GGUF_DIR = MODEL_DIR / "llm"               # 只放生成模型 GGUF
DEFAULT_CHAT_MODEL = "qwen2.5-coder-7b-instruct-q4_k_m"               # None 代表启动时自动选择第一个可用模型
PROMPT_DIR = PROJECT_ROOT / "config" / "prompts"
DEFAULT_PROMPT_NAME = "default"     # 提示词配置

# 后端加载优先级（你目前主要用 vllm，也可以只留一个）
LLM_BACKEND_PRIORITY = ["llama.cpp"]   # 顺序就是尝试顺序

# 如果使用 vLLM 的独立服务（openai兼容接口）
VLLM_API_BASE = os.getenv("VLLM_API_BASE", "http://localhost:8001/v1")   # 注意端口是否正确
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", None)                     # 可留空让它自动使用加载的模型

# =============================================
# Embedding 配置
# =============================================
EMBEDDING_SCAN_PATH = MODEL_DIR / "embedding"
DEFAULT_EMBEDDING = "bge-small-zh-v1.5"
EMBEDDING_BACKENDS = ["gguf", "huggingface"]
EMBEDDING_GGUF_SCAN_PATH = MODEL_DIR / "embedding_gguf"  # 新增：GGUF embedding 扫描目录
EMBEDDING_GGUF_DIR = MODEL_DIR / "embedding_gguf"  # 新增：专门放 GGUF 格式的 embedding 模型（可选独立目录，避免混淆）
DEFAULT_EMBEDDING_MODEL = "bge-small-zh-v1.5"      # 建议明确默认值（而不是 None）

EMBEDDING_SCAN_PATH = str(PROJECT_ROOT / "models" / "embedding")
EMBEDDING_GGUF_SCAN_PATH = str(PROJECT_ROOT / "models" / "embedding" / "gguf")

# RAG chunk 策略（你 capability.yaml 里也是 800/150）
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# =============================================
# 向量数据库
# =============================================
VECTOR_STORE_TYPE = "faiss"
VECTOR_DIM_AUTO = True

# =============================================
# 文件上传
# =============================================
MAX_UPLOAD_SIZE_MB = 100
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # 用于代码中直接比较
ALLOWED_TEXT_TYPES = ["txt", "md", "pdf"]   # 如果后续想支持 pdf 可以加

# =============================================
# 其他行为控制
# =============================================
STRICT_CAPABILITY_CHECK = True
AUTO_REGISTER_MODELS = True
# 建议新增：GPU 配置（用于 llama.cpp）
USE_GPU = True                                     # 或从环境变量读取
N_GPU_LAYERS = -1 if USE_GPU else 0                # -1 = 全 offload 到 GPU

# 建议新增：日志级别控制（方便调试）
LLAMA_CPP_VERBOSE = False                          # 是否打印 llama.cpp 详细加载日志（生产 False）