# DESIGN.md — baizeOS 前端

> 由已建成代码与截图（`.impeccable/review/`）记录，2026-08-24。
> 模式：**Operate**（完成任务型工具）。视觉世界：**暖色仪器**（Claude 风格，用户指定，brief-pinned）。

## 一句话

一台安静的本地产能仪器：暖象牙工作室里，陶土橙是唯一的声音，细线承担全部结构，衬线体只在"助手开口"时出现。

## 色板

唯一强调色制（Restrained）。所有色值定义于 `src/style/tokens.css`，明暗双套。

| 角色 | 浅色 | 深色 |
|---|---|---|
| 页面底 | `#FAF9F5` 象牙 | `#262624` 暖炭 |
| 凹陷底（侧栏/井） | `#F1EFE8` | `#20201F` |
| 浮起面（卡片/输入台） | `#FFFFFE` | `#2F2F2D` |
| 主文字 | `#1F1E1D` | `#F0EEE6` |
| 次级/弱文字 | `#55524A` / `#75725F` | `#C3C1B4` / `#99978B` |
| 细线 / 强线 | `#E8E5DB` / `#D7D4C6` | `#3B3A36` / `#4B4942` |
| **强调（陶土）** | `#C96342`（文字态 `#B05334`） | `#CD6746`（文字态 `#E39B7B`） |
| 语义 | ok `#5F7A44` · warn `#92650F` · danger `#B3402F` | `#93B474` / `#D8A94E` / `#E07862` |

- 主按钮 = 暖炭底米白字，**深色主题反转为米白底炭字**（`--btn-solid-*`）。
- 强调色用途：发送圆钮、RAG 激活态、用户消息气泡、品牌星标、激活导航图标、focus ring、代码复制悬停。除此之外页面保持无彩。
- 用户气泡直接用陶土橙实底白字——全页唯一的"大色块"，让"人说话"成为界面里最暖的东西。

## 字体

| 用途 | 栈 | 备注 |
|---|---|---|
| UI 正文 | Segoe UI Variable / Segoe UI / PingFang SC / Microsoft YaHei | 14px 基准，行高 1.6；聊天正文 15px |
| 声音时刻 | Georgia / Times / Source Han Serif / Noto Serif SC | **仅**品牌字标 `baizeOS`、问候语、关于页品牌行；CJK 回退宋体，大字号下的书卷气是有意选择 |
| 代码/数据 | Cascadia Code / Consolas | 代码块 13px；文件大小、日期、token 数一律 `tabular-nums` |

层级：页面题 22-23px/650 · 区块题 14px/600 · 卡片题 15.5px/600 · 正文 14-15px · 元信息 12-12.5px。字重只有 400/500/550/600 四档。

## 空间与形

- 间距节奏：4 的倍数；卡片内 16-17px，区块间 24-30px，标题上方间距大于下方。
- 圆角：`--r-sm 8`（小件）/ `--r-md 12`（卡片内件、toast）/ `--r-lg 16`（卡片、面板）/ `--r-xl 22`（输入台）；按钮与 chip 统一 10px；pill 用于状态件。
- **阴影只给浮层**（`--shadow-pop` 弹层、`--shadow-modal` 模态），平面元素靠 1px 细线分层；卡片悬停仅 `translateY(-2px)` + 线色加深 + pop 阴影。
- 内容列：对话 760px、设置 760px、知识库 1080px，全部居中。

## 组件语言

- **图标**：`ui/Icon.vue` 内联 SVG 系统，24 网格、1.6 描边、圆端点，继承 `currentColor`；禁止 emoji/Unicode 充当图标。
- **按钮**（`ui/AppButton.vue`）：solid（暖炭）/ soft（面+线）/ ghost / danger 四态；loading 内联旋转环并禁点。
- **弹层**（`ui/AppModal.vue`）：teleport + 遮罩 32% 暖黑、pop 进场（6px 上浮+缩放 0.98）、焦点圈定、Esc 关闭、滚动锁；确认框经 `settings.confirm()` Promise 化。
- **下拉**（`ui/AppSelect.vue`）：teleport 定位、空间不足自动上翻、完整键盘导航（方向/Home/End/Esc）、chip 与 field 两种形态。
- **Toast**（右上堆叠，success/error/info 图标色分，点击即散，错误驻留 6s）。
- **空状态**（`ui/EmptyState.vue`）：陶土软底圆角图标砖 + 标题 + 指引 + CTA，文案必须说明"放什么、怎么开始"。
- **代码块**：`code-head`（语言标签 + 复制钮）+ `pre` 双层，明暗各一套从暖色板派生的 hljs 配色（见 `style/markdown.css`）。

## 标志性瞬间

1. **流式呼吸**：助手回复时，渲染末尾出现陶土色方块光标（1s 步进闪烁）；空态星标以 4.5s 周期轻旋呼吸——"本地模型在思考"的拟物表达。
2. **星标徽记**：六笔星芒（白泽符号）贯穿品牌位、助手头像、RAG chip、空态——同一个符号反复出现，是整个系统的记忆点。

## 浏览器表面（craft floor）

选区 = 陶土 22% 色 · 光标 caret = 陶土 · 滚动条细杆 = 强线色（悬停弱文字色）· focus ring = 2px 陶土外描 · 数字全 tabular · `prefers-reduced-motion` 下全部动效归零。

## 动效语法

统一 `ease-out / cubic-bezier(0.16,1,0.3,1)`，150-250ms。视图切换 = 淡入 + 6px 上浮；弹层 = pop；卡片悬停 -2px。无弹跳、无渐变文字、无玻璃拟态。

## 已验证

- `vue-tsc -b && vite build` 零报错（Vite 7.3.6）。
- 截图（`.impeccable/review/`）：desktop 1440 浅色对话空态 ✓ · mobile 500 深色窄屏（无裁切，探针实测 vw=chat=content）✓ · kb 空态 ✓ · settings ✓。
- 已知边界：headless 最小窗宽 ~500px，390 真机视口经构造验证（单列网格 `min(100%,250px)` + 副标题折行）。
