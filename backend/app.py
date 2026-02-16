# backend/app.py
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# ------------------------------
from app import create_app   # 注意这里还是 from app import ...

app = create_app()

print("\n=== 所有已注册路由 ===")
for rule in app.url_map.iter_rules():
    print(f"{rule.methods} → {rule}")
print("=====================\n")

if __name__ == "__main__":
    # print(app.url_map)
    # print("=================================")
    # print(" BaizeOS Backend Starting")
    # print(f" Host: 0.0.0.0")
    # print(f" Port: 5000")
    # print(f" Debug: True (可手动改成 False)")
    # print("=================================")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,          # ← 你想要随时改 debug 就直接在这里改这一行
        use_reloader=True,
    )