<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useKbStore } from '@/stores/kb'
import { useSettingsStore } from '@/stores/settings'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import Icon from '@/ui/Icon.vue'

const chat = useChatStore()
const kbStore = useKbStore()
const settings = useSettingsStore()

const scrollEl = ref<HTMLElement | null>(null)
const composerRef = ref<InstanceType<typeof ChatComposer> | null>(null)
const stickToBottom = ref(true)
const showJump = ref(false)

// ============ 滚动 ============
function onScroll() {
  const el = scrollEl.value
  if (!el) return
  const distance = el.scrollHeight - el.scrollTop - el.clientHeight
  stickToBottom.value = distance < 120
  showJump.value = distance > 300
}

function scrollToBottom(smooth = false) {
  const el = scrollEl.value
  if (!el) return
  el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
}

watch(
  () => [chat.messages.length, chat.messages[chat.messages.length - 1]?.content] as const,
  async () => {
    await nextTick()
    // 新消息与流式增长都只在已吸底时跟随
    if (stickToBottom.value) scrollToBottom()
  },
)

// ============ 代码块复制（事件委托，渲染后的 HTML 无法绑定 Vue 事件） ============
function onRootClick(e: MouseEvent) {
  const btn = (e.target as HTMLElement).closest('[data-code-copy]')
  if (!btn) return
  const block = btn.closest('.code-block')
  const code = block?.querySelector('pre code')?.textContent ?? ''
  navigator.clipboard.writeText(code).then(
    () => {
      btn.textContent = '已复制'
      window.setTimeout(() => {
        btn.textContent = '复制'
      }, 1600)
    },
    () => settings.toast('复制失败', 'error'),
  )
}

// ============ 拖拽上传附件 ============
let dragDepth = 0
const dragging = ref(false)

function onDragEnter(e: DragEvent) {
  if (!e.dataTransfer?.types.includes('Files')) return
  dragDepth++
  dragging.value = true
}

function onDragOver(e: DragEvent) {
  if (!e.dataTransfer?.types.includes('Files')) return
  e.preventDefault()
}

function onDragLeave() {
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) dragging.value = false
}

async function onDrop(e: DragEvent) {
  e.preventDefault()
  dragDepth = 0
  dragging.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  if (!files.length) return
  await composerRef.value?.uploadFiles(files)
}

onMounted(() => {
  void kbStore.fetchList().catch(() => undefined)
  void chat.refreshTmpFiles()
})

onBeforeUnmount(() => {
  dragDepth = 0
})

// ============ 建议提问 ============
const SUGGESTIONS = [
  { icon: 'cpu', text: '帮我用 Python 写一个快速排序' },
  { icon: 'library', text: '解释一下什么是向量数据库' },
  { icon: 'spark', text: '用通俗的语言介绍 RAG 技术' },
  { icon: 'file', text: '帮我总结一份文档的要点' },
] as const

function pickSuggestion(text: string) {
  composerRef.value?.setDraft(text)
}

async function handleNewChat() {
  if (chat.streaming) chat.stop()
  chat.newChat()
  stickToBottom.value = true
  composerRef.value?.focus()
}
</script>

<template>
  <div
    class="chat"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="onRootClick"
  >
    <!-- 空状态 -->
    <div v-if="!chat.messages.length" class="chat__hero">
      <div class="hero-mark" aria-hidden="true">
        <Icon name="spark" :size="30" :stroke-width="1.6" class="hero-mark__svg" />
      </div>
      <h1 class="hero-title">你好，我是 白泽。</h1>
      <p class="hero-sub">本地知识库问答助手 —— 上传文档、构建知识库、随时提问。</p>

      <div class="hero-suggestions">
        <button
          v-for="s in SUGGESTIONS"
          :key="s.text"
          class="suggestion"
          type="button"
          @click="pickSuggestion(s.text)"
        >
          <Icon :name="s.icon" :size="15" />
          {{ s.text }}
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div v-else ref="scrollEl" class="chat__scroll" @scroll.passive="onScroll">
      <div class="chat__thread">
        <ChatMessage
          v-for="(m, i) in chat.messages"
          :key="m.id"
          :msg="m"
          :is-last="i === chat.messages.length - 1"
          @regenerate="chat.regenerate()"
        />
      </div>
    </div>

    <!-- 会话工具条 -->
    <div v-if="chat.messages.length" class="chat__tools">
      <button class="tool-pill" type="button" @click="handleNewChat">
        <Icon name="plus" :size="14" />
        新对话
      </button>
    </div>

    <!-- 回到底部 -->
    <Transition name="fade">
      <button v-if="showJump && chat.messages.length" class="jump-btn" type="button" aria-label="回到底部" @click="scrollToBottom(true); stickToBottom = true">
        <Icon name="chevron-down" :size="16" />
      </button>
    </Transition>

    <!-- 输入台 -->
    <div class="chat__dock">
      <ChatComposer ref="composerRef" />
    </div>

    <!-- 拖拽遮罩 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="dragging" class="drop-overlay">
          <div class="drop-card">
            <Icon name="upload" :size="26" />
            <p>松开以上传到本对话</p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chat__scroll {
  flex: 1;
  overflow-y: auto;
}

.chat__thread {
  max-width: 760px;
  margin: 0 auto;
  padding: 26px clamp(14px, 3vw, 24px) 12px;
}

/* ============ 空状态 ============ */

.chat__hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px 8px;
  min-height: 0;
  overflow-y: auto;
}

.chat__hero > * {
  max-width: 100%;
}

.hero-mark {
  width: 62px;
  height: 62px;
  display: grid;
  place-items: center;
  border-radius: 20px;
  background: var(--surface);
  border: 1px solid var(--line);
  color: var(--accent-text);
  box-shadow: var(--shadow-pop);
  margin-bottom: 22px;
}

.hero-mark__svg {
  animation: mark-breathe 4.5s ease-in-out infinite;
}

@keyframes mark-breathe {
  0%,
  100% {
    transform: rotate(0deg) scale(1);
  }
  50% {
    transform: rotate(45deg) scale(1.06);
  }
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(26px, 3.4vw, 34px);
  font-weight: 500;
  letter-spacing: -0.01em;
}

.hero-sub {
  margin-top: 9px;
  font-size: 14.5px;
  color: var(--ink-3);
  max-width: 100%;
  padding: 0 16px;
}

.hero-suggestions {
  margin-top: 30px;
  width: 100%;
  max-width: 560px;
  padding: 0 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr));
  gap: 9px;
}

.suggestion {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 15px;
  font-size: 13.5px;
  color: var(--ink-2);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  text-align: left;
  transition:
    border-color 0.15s ease-out,
    transform 0.15s ease-out,
    color 0.15s ease-out;
}

.suggestion svg {
  color: var(--accent-text);
  flex-shrink: 0;
}

.suggestion:hover {
  border-color: var(--accent-tint-line);
  transform: translateY(-1px);
  color: var(--ink);
}

/* ============ 输入台停靠 ============ */

.chat__dock {
  flex-shrink: 0;
  width: min(760px, 100%);
  margin: 0 auto;
  padding: 8px clamp(14px, 3vw, 24px) 18px;
}

.jump-btn {
  position: absolute;
  left: 50%;
  bottom: 132px;
  transform: translateX(-50%);
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  box-shadow: var(--shadow-pop);
  color: var(--ink-2);
}

.jump-btn:hover {
  color: var(--ink);
}

.chat__tools {
  position: absolute;
  top: 14px;
  right: 22px;
  z-index: 10;
}

.tool-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 13px;
  font-size: 12.5px;
  color: var(--ink-3);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 999px;
  transition:
    border-color 0.15s ease-out,
    color 0.15s ease-out;
}

.tool-pill:hover {
  border-color: var(--accent-tint-line);
  color: var(--accent-text);
}

/* ============ 拖拽遮罩 ============ */

.drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 95;
  background: var(--overlay);
  display: grid;
  place-items: center;
  pointer-events: none;
}

.drop-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 34px 52px;
  border: 2px dashed var(--accent-tint-line);
  border-radius: var(--r-lg);
  background: var(--surface);
  color: var(--accent-text);
  font-size: 14.5px;
  box-shadow: var(--shadow-modal);
}
</style>
