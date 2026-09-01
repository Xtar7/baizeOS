# baizeOS 前端

基于本地大模型的 RAG 知识库问答系统的 Web 前端。Vue 3 + TypeScript + Vite 7，无 UI 组件库依赖（自绘组件 + 内联 SVG 图标），视觉语言参照 Claude：暖象牙底色、陶土橙强调、细线边框、衬线「助手声音」时刻。

## 技术栈

| 层 | 选型 |
|---|---|
| 框架 | Vue 3.5（Composition API + `<script setup>`） |
| 构建 | Vite 7 · vue-tsc 类型检查 |
| 状态 | Pinia 3（settings / kb / chat） |
| 路由 | Vue Router 4（对话 / 知识库 / 设置） |
| HTTP | Axios 1.x（REST）+ fetch ReadableStream（SSE 流式对话） |
| Markdown | markdown-it + highlight.js（按需注册 16 种语言） |

## 运行

```bash
# 先启动后端 Flask（localhost:5000）
cd ../backend && uv run python app.py

# 启动前端（localhost:3000，/v1 已代理到后端）
pnpm install   # 或 npm install
pnpm dev
```

生产构建：

```bash
pnpm build     # vue-tsc -b && vite build → dist/
```

将 `dist/` 内容复制到 Flask 的静态目录即可由后端直接托管。

## 目录

```
src/
├─ api/            # 接口层：request(axios) / kb / chat(SSE) / file / model
├─ stores/         # Pinia：settings(主题+toast+confirm) / kb / chat
├─ types/api.ts    # 与 docs/接口规范.md 一一对应的类型
├─ ui/             # 自绘基础件：Icon / AppButton / AppModal / AppSelect / Toast…
├─ components/     # SideBar / chat/* / kb/*
├─ views/          # Layout / ChatView / KnowledgeView / KbDetailView / SettingsView
└─ style/          # tokens.css(设计令牌) / base.css(浏览器表面主题化) / markdown.css
```

## 接口契约要点（实现已严格遵守）

1. 上传 form-data 文件字段名必须是 `file`（单数）；KB 上传带 `kb_id`，临时文件带 `chat_id`。
2. 删除知识库 / KB 文件：`DELETE` + JSON body；批量字段用复数（`kb_ids` / `kb_file_ids`）。
3. 临时文件列表与删除：`POST /v1/files/list`、`POST /v1/files/delete`。
4. 对话：`POST /v1/chat/completions`，RAG 模式附 `rag: true, kb_id`；流式 SSE 的结束帧携带 `usage / references / safety`，前端据此渲染引用卡片与未命中提示。
5. 更新知识库返回 `needs_rebuild: true` 时，界面弹出重建横幅，一键调 `POST /v1/kb/{id}/reindex`。

详细字段见 `../docs/API调用方案.md` 与 `../docs/接口规范.md`。
