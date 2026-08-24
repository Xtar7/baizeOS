# baizeOS
这是一个通用的知识库问答系统，依托于本地的大模型来构建RAG知识库，同时我的目标是可以同时构建多个知识库，能够选择数据库，能够选择基座大模型，然后类似于lmstudio~

## 快速开始

```bash
# 方式一（Windows 推荐）：双击 start.bat
# 方式二：命令行
python start.py
```

`start.py` 会自动完成：检查 uv / Node 环境 → 首次运行时安装前端依赖 → 启动 Flask 后端（localhost:5000）→ 启动 Vite 前端（localhost:3000）→ 打开浏览器。`Ctrl+C` 一起退出。

手动分别启动：

```bash
# 后端
cd backend && uv run python app.py

# 前端（pnpm）
cd frontend && pnpm install && pnpm dev
```

## 目录

| 目录 | 说明 |
|---|---|
| `backend/` | Flask 后端（RAG、知识库、临时文件、LLM 服务） |
| `frontend/` | Vue 3 + TS + Vite 前端（详见 `frontend/README.md`） |
| `docs/` | 接口规范、API 调用方案、前端设计方案 |
| `KB/` | 知识库文件存储 |
| `models/` | 本地 GGUF / Embedding 模型 |
