# backend/app.py
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# ------------------------------
from app import create_app
from app.utils.json_provider import NumpyJSONProvider

app = create_app()
app.json = NumpyJSONProvider(app)

# 启动诊断：注意不要在这里 import torch / 扫描 embedding —— create_app()
# 已经做过一次，重复扫描只会拖慢启动并制造重复日志。
print("\n=== 系统启动诊断 ===")
print(f"PROJECT_ROOT: {project_root}")
print("=====================\n")

print("\n=== 所有已注册路由 ===")
for rule in sorted(app.url_map.iter_rules(), key=str):
    print(f"{sorted(rule.methods - {'HEAD', 'OPTIONS'})} → {rule}")
print("=====================\n")


if __name__ == "__main__":
    # reloader 会 fork 出第二个进程再把整个应用（含 4~5GB 的 GGUF 权重）
    # 加载一遍，内存直接翻倍。在单进程下用 threaded 即可满足 SSE 并发。
    use_reloader = os.getenv("BAIZE_FLASK_RELOAD", "0") == "1"
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=app.config.get("DEBUG", False),
        use_reloader=use_reloader,
        threaded=True,
    )
