# baizeOS · 白泽

> 🇨🇳 **这是中文 README（项目主入口）。** 英文版请见 [README.en.md](./README.en.md).

> **在你自己电脑上跑的 RAG 知识库问答助手——完全离线，完全由你掌控。**
> baizeOS 把本地 GGUF 大模型和你本地的 `.txt` / `.md` / `.pdf` 文档通过向量索引串起来，每条回答都附带它实际引用过的原文片段。

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-232323.svg)](./LICENSE)
[![Vue 3](https://img.shields.io/badge/前端-Vue%203%20%2B%20TS-4F8F4F.svg)](#技术栈)
[![Flask](https://img.shields.io/badge/后端-Flask%20%2B%20llama--cpp-C96342.svg)](#技术栈)
[![本地优先](https://img.shields.io/badge/隐私-100%25%20本地推理-1f1e1d.svg)](#隐私)
[![Stars](https://img.shields.io/github/stars/Xtar7/baizeOS?style=flat)](../../stargazers)
[![en](https://img.shields.io/badge/lang-English-232323.svg)](./README.en.md)
[![en](https://img.shields.io/badge/lang-English-232323.svg)](./README.en.md)

<br>
<img width="1280" height="640" alt="hero" src="https://github.com/user-attachments/assets/af97064f-5b70-4d15-be72-cba5e7d89d42" />

<br>

## baizeOS 是什么？

baizeOS（白泽）是一个面向单用户的 RAG 工作站。技术栈刻意保持小而精：

* **Flask** 后端：用 `llama-cpp-python` 跑 GGUF 模型，用 `FAISS` 建文档向量索引，用 `sentence-transformers` 做文本嵌入，对话补全通过 **Server-Sent Events** 流式返回。
* **Vue 3 + TypeScript** 前端：完全不依赖任何 UI 组件库——所有控件都是手绘的，以保证视觉语言的一致性。

产品遵循三条原则：

1. **完全本地。** 没有埋点、没有云端回传、没有 API Key。你的文档和对话永远不离开这台机器。
2. **回答可溯源。** 每一轮助手回复后面都会跟一个 `references` 区块，列出模型实际看过的原文片段。如果索引没命中，界面会明确显示出来——模型永远不会自说自话。
3. **克制的设计。** 暖象牙底色，唯一一抹陶土橙强调色，细线边框承担结构层级，衬线字只用在助手的"声音"时刻。完整设计令牌见 [`DESIGN.md`](./DESIGN.md)。

---

## 目录

- [亮点](#亮点)
- [截图](#截图)
- [快速开始](#快速开始)
- [技术栈](#技术栈)
- [架构](#架构)
- [项目结构](#项目结构)
- [前端详解](#前端详解)
- [接口契约](#接口契约)
- [路线图](#路线图)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 亮点

- 🔌 **一键启动。** `python start.py` 同时拉起 Flask（`:5000`）和 Vite（`:3000`），首次运行会自动安装前端依赖，两端都就绪后自动打开浏览器。
- 📚 **多知识库。** 想建几个就建几个，每个知识库可以独立选择嵌入模型和系统提示词，侧栏一键切换。
- 🧠 **RAG 是一等公民，不是补丁。** SSE 流末尾会带 `usage` / `references` / `safety` 三个帧，前端直接据此渲染引用卡片和未命中提示。
- 🖼 **引用肉眼可见。** 每一轮回复都展示检索到的原文片段。索引没命中时会显示"无命中"状态，让你随时知道模型是不是在即兴发挥。
- 🎨 **手绘 UI，不用组件库。** 所有图标都是内联 SVG，所有模态框都走 teleport，所有下拉框都支持完整键盘导航。详见 [`frontend/src/ui/`](./frontend/src/ui)。
- 🌗 **亮 / 暗双主题，同一套暖色令牌。** 没有纯黑暗模式，没有冷蓝亮模式——只是亮度变化。

---

## 截图

| 对话 | 知识库 | 设置 |
| :---: | :---: | :---: |
| ![对话](./.impeccable/review/desktop.png) | ![知识库](./.impeccable/review/kb.png) | ![设置](./.impeccable/review/settings.png) |

全分辨率审阅截图见 [`.impeccable/review/`](./.impeccable/review)。

---

## 快速开始

### 准备

* **Python ≥ 3.10**，推荐用 [`uv`](https://docs.astral.sh/uv/)，`pip` 也行
* **Node.js ≥ 18**，推荐 `pnpm`（`npm` / `yarn` 也能用）
* 一份 **GGUF 模型**，放到 `models/` 目录下，详见下方[后端模型放置](#后端模型放置)
* **操作系统：** Windows 10+ / macOS 12+ / Linux

### 一键启动

```bash
git clone https://github.com/Xtar7/baizeOS.git
cd baizeOS
python start.py          # Windows 用户可以双击 start.bat
```

`start.py` 会自动完成以下步骤：

1. 检查 `uv` 和 `node` 是否可用
2. 首次运行时自动安装前端依赖
3. 启动 Flask（`localhost:5000`）和 Vite（`localhost:3000`）
4. 两端都就绪后自动打开浏览器到 <http://localhost:3000>
5. `Ctrl+C` 一次性退出并清理两个子进程

### 手动启动

如果你想分别控制前后端：

```bash
# 后端（Flask :5000）
cd backend
uv run python app.py

# 前端（Vite :3000，/v1 已代理到后端）
cd frontend
pnpm install
pnpm dev
```

前端生产构建：

```bash
cd frontend
pnpm build              # vue-tsc -b && vite build → dist/
```

把 `dist/` 目录的内容丢到 Flask 的静态目录里，后端就能直接托管整个 SPA。

### 后端模型放置

1. 把一份 GGUF 模型放到 `models/` 下，比如 `models/Qwen2.5-7B-Instruct-Q4_K_M.gguf`。
2. 把一份 sentence-transformers 嵌入模型放到 `models/` 下，比如 `models/bge-small-en-v1.5/`。
3. 编辑 `start.py`（或者显式传参），让后端指向正确的文件路径。默认假设是一份 GGUF 文件 + `bge-small` 家族的嵌入模型。

如果暂时没有模型，前端依然能起来，并会提示你后端不在线——方便你光看 UI。

---

## 技术栈

| 层 | 选型 | 为什么 |
|---|---|---|
| **大模型推理** | `llama-cpp-python` | 纯 C++ 推理，CPU 友好，原生支持 GGUF |
| **API 服务** | Flask 3 | 极简，可读，没有黑魔法；流式通过生成器响应 |
| **向量索引** | `faiss-cpu` | 默认小语料用 IndexFlatIP；不需要单独起服务 |
| **文本嵌入** | `sentence-transformers` | 本地 ONNX / PyTorch 推理——零网络请求 |
| **前端框架** | Vue 3 + TypeScript + Vite 7 | Composition API + `<script setup>`，完整类型安全 |
| **状态管理** | Pinia 3 | `settings`（主题 + toast + 确认弹窗 Promise）/ `kb` / `chat` |
| **HTTP** | Axios 1.x 处理 REST，`fetch` 的 `ReadableStream` 处理 SSE | 浏览器里 Axios没法增量读流 |
| **Markdown** | `markdown-it` + `highlight.js`（按需注册 16 种语言） | 客户端 bundle 不会臃肿 |

---

## 架构

```
┌────────────────────┐     SSE /v1/chat/completions      ┌────────────────────┐
│   Vue 3 SPA        │ ───────────────────────────────▶│   Flask 后端       │
│   (localhost:3000) │                                  │   (localhost:5000) │
│                    │ ◀───  流式 delta token  ────────│                    │
│  · ChatView        │                                  │  · /v1/chat        │
│  · KnowledgeView   │     REST  /v1/kb, /v1/files      │  · /v1/kb          │
│  · SettingsView    │ ───────────────────────────────▶│  · /v1/files       │
└────────────────────┘                                  │  · /v1/models      │
                                                          └────────┬───────────┘
                                                                   │
                                                          ┌────────▼──────────┐
                                                          │  llama-cpp-python  │
                                                          │  sentence-trans.   │
                                                          │  faiss-cpu         │
                                                          └────────────────────┘
```

每一轮对话都走同一个 SSE 响应：`delta` 事件流式输出 token，最后一个 `done` 事件带上 `usage`、`references`、`safety` 三类元数据。前端用 `fetch` + `ReadableStream` 读流，stream 一关就立刻渲染引用卡片。

---

## 项目结构

```
baizeOS/
├─ start.py                 # 一键启动器（Flask + Vite）
├─ start.bat                # Windows 启动包装
├─ backend/                 # Flask + llama-cpp + FAISS
│  ├─ app/                  # 路由、服务、RAG、OCR
│  ├─ data/                 # SQLite / 本地状态
│  └─ pyproject.toml
├─ frontend/                # Vue 3 SPA
│  ├─ src/
│  │  ├─ api/               # request, chat (SSE), kb, file, model
│  │  ├─ stores/            # Pinia: settings, kb, chat
│  │  ├─ types/             # 对应 docs/接口规范.md 的类型
│  │  ├─ ui/                # 手绘基础件（Icon, AppButton, ...）
│  │  ├─ components/        # SideBar, chat/*, kb/*
│  │  ├─ views/             # Layout, ChatView, KnowledgeView, KbDetailView, SettingsView
│  │  └─ style/             # tokens.css · base.css · markdown.css
│  └─ vite.config.ts
├─ docs/                    # 接口规范、设计说明、截图
├─ KB/                      # （运行时）各知识库的文档存储
├─ models/                  # （运行时）GGUF + 嵌入模型
├─ DESIGN.md                # 设计令牌 & 组件契约
├─ PRODUCT.md               # 产品上下文
├─ README.md                # 英文 README
├─ README.zh-CN.md          # 本文件
└─ LICENSE                  # MIT
```

---

## 前端详解

前端完全类型化，**不**依赖任何 UI 组件库，所有视觉都收敛在一套紧预算里：

- **`tokens.css`** 是唯一真理源。所有色值、圆角、阴影、字体都集中在这里。亮 / 暗主题共用同一套暖色板——只调亮度。
- **`ui/Icon.vue`** 运行时渲染内联 SVG 图标，24 网格，1.6 描边，圆头，`currentColor`。没有 emoji，没有 Unicode 替代。
- **`AppModal.vue`** 走 teleport，自动聚焦、滚动锁、Esc 关闭。确认弹窗通过 `settings.confirm()` 返回 Promise，业务逻辑保持声明式。
- **`AppSelect.vue`** 支持完整键盘导航（↑ ↓ Home End Esc），下方空间不足时自动向上翻转。
- **`AppButton.vue`** 四种状态（solid / soft / ghost / danger），loading 时内联旋转环并禁用点击。
- **`style/markdown.css`** 提供**两套** `hljs` 代码高亮配色——一套亮主题、一套暗主题——都从同一套暖色令牌派生。
- **`RAG` chip 是侧栏里唯一的彩色**——一旦开启，聊天头部会泛出陶土橙，助手回复后会跟一张引用卡片。
- **流式光标** 是个陶土方块，1s 渐入 / 1s 渐出地呼吸。空状态是品牌标以 4.5s 周期慢旋——*"本地模型正在思考"*的拟物表达。

完整设计系统——每一个令牌、每一个组件契约、每一种动效——见 [`DESIGN.md`](./DESIGN.md)。

---

## 接口契约

REST + SSE 接口契约完整定义在 [`docs/接口规范.md`](./docs/接口规范.md) 和 [`docs/API调用方案.md`](./docs/API调用方案.md)。前端严格实现了下面几条硬规则：

1. **上传 form-data** 的字段名必须是 `file`（单数）。知识库上传额外加 `kb_id`，临时会话文件加 `chat_id`。
2. **DELETE 带 JSON body。** 批量字段是复数：`kb_ids` / `kb_file_ids`。
3. **临时文件的列表 / 删除** 用 `POST /v1/files/list` 和 `POST /v1/files/delete`（不是 `GET` / `DELETE`）。
4. **RAG 对话** 是 `POST /v1/chat/completions`，附 `rag: true` 和 `kb_id`。SSE 流末尾的最后一帧带 `usage` / `references` / `safety`，前端据此渲染。
5. **知识库编辑** 改了嵌入模型后会返回 `needs_rebuild: true`。UI 弹出"重建"横幅，点击后调 `POST /v1/kb/{id}/reindex`。

如果你要接新的前端或者换模型，请先把 [`docs/API调用方案.md`](./docs/API调用方案.md) 通读一遍再开工。

---

## 路线图

- [x] 多知识库，每个知识库独立配置系统提示词和嵌入模型
- [x] RAG 模式带引用渲染 + "无命中"空状态
- [x] 亮 / 暗主题，共用同一套暖色令牌
- [x] 内联 SVG 图标系统，全键盘导航
- [ ] 多模态知识库（图片、扫描件 PDF，走 `backend/app/ocr` 里已有的 OCR 流水线）
- [ ] 对话导出（Markdown / JSON）
- [ ] 可选的检索增强 reranker 模型
- [ ] 本地 Web 搜索适配器（默认关闭）

---

## 贡献指南

欢迎 PR。简单说几句：

1. **先开 issue**，除非只是改一行。`DESIGN.md` 里的令牌集和 `docs/接口规范.md` 里的接口约定都是承重的——改这两处要打个招呼。
2. **推送前跑构建**：
   ```bash
   cd frontend && pnpm build           # vue-tsc + Vite，必须零报错
   cd backend  && python -m py_compile $(find app -name "*.py")
   ```
3. **风格保持一致。** Vue 组件用 `<script setup lang="ts">`。后端是朴素的 Flask——别整蓝图魔法、别上 ORM。注释稀疏，英文；标识符要有描述性。
4. **不要新增依赖，除非 PR 里写明理由。** 前后端都故意保持小。

---

## 使用条款 · 反 996

本项目欢迎个人开发者、学术研究、非商业组织使用。**对**实行以下任一超时工作制度的组织及其员工，**禁止使用本项目**：

- **"996"** —— 早 9 点至晚 9 点、每周工作 6 天的作息安排
- **"大小周"** —— 单双周交替、单休与双休轮换的作息安排
- **任何超过当地劳动法规定上限的工作时间安排**（包括但不限于每月加班超过 36 小时的法定上限）

**适用范围**：

- 上述组织**直接使用**本项目
- 上述组织**将本项目作为网络服务**向第三方提供（即便是基于本项目二次包装）
- 上述组织**将本项目整合进商业产品**中再分发

**不适用范围**：

- 个人开发者用于学习、研究、个人作品
- 严格遵守当地劳动法工时上限的组织
- 行为准则能合理证明其全部员工均不超时工作的组织

如果你所在的公司实行上述制度，请**不要**使用本项目，并欢迎向身边同事推荐遵守劳动法的工作环境。这是一条**社区规范**，不是合同条款；其精神基于相信技术从业者有权拒绝超时工作。

---

## 许可证

[GPL-3.0](./LICENSE) — © 2026 Xtar。任何人都可以自由使用、修改、分发，但**所有衍生作品必须同样以 GPL-3.0 开源**。商业使用允许，但必须回馈社区。

<br>

<sub>baizeOS · 白泽 —— "能识万物之言者。"</sub>
