# backend/app.py
import sys
from pathlib import Path
import torch

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# ------------------------------
from app import create_app
from app.services.embedding_factory import scan_embedding_models

app = create_app()

# 启动时打印关键信息
print("\n=== 系统启动诊断 ===")
print(f"PROJECT_ROOT: {project_root}")
print(f"GPU 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU 设备: {torch.cuda.get_device_name(0)}")
    print(f"CUDA 版本: {torch.version.cuda}")
print("=====================\n")

# 扫描 embedding 模型（包括 GGUF）
scan_embedding_models()

print("\n=== 所有已注册路由 ===")
for rule in app.url_map.iter_rules():
    print(f"{rule.methods} → {rule}")
print("=====================\n")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=True,
    )