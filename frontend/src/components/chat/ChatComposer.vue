<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useKbStore } from '@/stores/kb'
import { useSettingsStore } from '@/stores/settings'
import Icon from '@/ui/Icon.vue'
import AppSelect from '@/ui/AppSelect.vue'
import type { SelectOption } from '@/ui/AppSelect.vue'
import { formatBytes, extOf } from '@/utils/format'

const chat = useChatStore()
const kbStore = useKbStore()
const settings = useSettingsStore()

const draft = ref('')
const focused = ref(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const panelOpen = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

function autoGrow() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 190)}px`
}

function focus() {
  void nextTick(() => textareaRef.value?.focus())
}

function setDraft(text: string) {
  draft.value = text
  autoGrow()
  focus()
}

// ============ 发送（IME 安全：组合输入中的 Enter 不触发） ============
function canSend() {
  return !!draft.value.trim() && !chat.streaming
}

function onKeydown(e: KeyboardEvent) {
  if (e.isComposing || e.keyCode === 229) return
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    void doSend()
  }
}

async function doSend() {
  if (!canSend()) return
  const text = draft.value
  const names = chat.tmpFiles.map((f) => f.filename)
  draft.value = ''
  await nextTick()
  autoGrow()
  await chat.send(text, names)
  focus()
}

// ============ RAG / 知识库选择 ============
const kbOptions = computed<SelectOption[]>(() =>
  kbStore.list.map((k) => ({
    label: k.display_name,
    value: k.kb_id,
    meta: `${k.file_count} 个文件`,
  })),
)

async function toggleRag() {
  if (!chat.ragEnabled && !kbStore.list.length) {
    await kbStore.fetchList(true).catch(() => undefined)
    if (!kbStore.list.length) {
      settings.toast('还没有知识库，先到「知识库」页创建一个', 'info')
      return
    }
  }
  chat.ragEnabled = !chat.ragEnabled
  if (chat.ragEnabled && !chat.selectedKbId && kbOptions.value.length) {
    const first = kbOptions.value[0]
    if (first) chat.selectedKbId = first.value
  }
  focus()
}

function onKbChange(v: string) {
  chat.selectedKbId = v
  if (!v) chat.ragEnabled = false
  else chat.ragEnabled = true
}

const selectedKbName = computed(
  () => kbStore.list.find((k) => k.kb_id === chat.selectedKbId)?.display_name ?? '',
)

// ============ 附件 ============
onMounted(() => {
  void chat.refreshTmpFiles()
})

function pickFiles() {
  fileInputRef.value?.click()
}

async function onFilesChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  if (!files.length) return
  await uploadFiles(files)
}

/** 由 ChatView 的拖拽逻辑调用 */
async function uploadFiles(files: File[]) {
  if (uploading.value) return
  uploading.value = true
  try {
    const res = await chat.addTmpFiles(files)
    if (res.ok) settings.toast(`已上传 ${res.ok} 个附件`, 'success')
    for (const name of res.failed) settings.toast(`${name} 上传失败`, 'error')
  } catch {
    settings.toast('附件上传失败，请检查后端服务', 'error')
  } finally {
    uploading.value = false
  }
}

defineExpose({ focus, setDraft, uploadFiles })

async function removeTmp(id: string) {
  try {
    await chat.removeTmpFile(id)
  } catch {
    settings.toast('删除附件失败', 'error')
  }
}

async function clearAll() {
  if (!chat.tmpFiles.length) return
  const ok = await settings.confirm({
    title: '清空全部附件？',
    body: `将删除本对话已上传的 ${chat.tmpFiles.length} 个临时文件。`,
    confirmText: '清空',
    danger: true,
  })
  if (!ok) return
  try {
    await chat.clearTmpFiles()
    settings.toast('附件已清空', 'success')
  } catch {
    settings.toast('清空失败', 'error')
  }
}

const FILE_ICON: Record<string, string> = {
  pdf: 'file',
  md: 'file',
  txt: 'file',
}
</script>

<template>
  <div class="composer-wrap">
    <!-- 附件面板 -->
    <Transition name="pop">
      <div v-if="panelOpen" class="attach-panel">
        <header class="attach-panel__head">
          <span>聊天附件</span>
          <button
            v-if="chat.tmpFiles.length"
            class="attach-clear"
            type="button"
            @click="clearAll"
          >
            清空全部
          </button>
        </header>

        <p class="attach-panel__hint">上传的文件将作为本对话的上下文（随会话保存）。</p>

        <ul v-if="chat.tmpFiles.length" class="attach-list">
          <li v-for="f in chat.tmpFiles" :key="f.tmp_file_id" class="attach-item">
            <Icon :name="FILE_ICON[extOf(f.filename)] ?? 'clip'" :size="14" />
            <span class="attach-item__name">{{ f.filename }}</span>
            <span class="attach-item__size tabular">{{ formatBytes(f.bytes) }}</span>
            <button class="attach-item__del" type="button" :aria-label="`删除 ${f.filename}`" @click="removeTmp(f.tmp_file_id)">
              <Icon name="x" :size="13" />
            </button>
          </li>
        </ul>
        <p v-else class="attach-empty">还没有附件</p>

        <button class="attach-add" type="button" @click="pickFiles">
          <Icon name="plus" :size="14" />
          添加文件
        </button>
      </div>
    </Transition>

    <div class="composer" :class="{ 'is-focused': focused }">
      <textarea
        ref="textareaRef"
        v-model="draft"
        class="composer__input"
        rows="1"
        placeholder="输入消息，Ctrl + Enter 发送…"
        aria-label="输入消息"
        @keydown="onKeydown"
        @input="autoGrow"
        @focus="focused = true"
        @blur="focused = false"
      />

      <div class="composer__bar">
        <div class="composer__tools">
          <button
            class="tool-btn"
            :class="{ 'is-on': panelOpen }"
            type="button"
            aria-label="附件"
            title="聊天附件"
            @click="panelOpen = !panelOpen"
          >
            <Icon name="clip" :size="16" />
            <span v-if="chat.tmpFiles.length" class="tool-badge tabular">{{ chat.tmpFiles.length }}</span>
          </button>

          <button
            class="rag-toggle"
            :class="{ 'is-on': chat.ragEnabled }"
            type="button"
            role="switch"
            :aria-checked="chat.ragEnabled"
            title="检索增强生成"
            @click="toggleRag"
          >
            <Icon name="spark" :size="14" />
            <span>RAG</span>
          </button>

          <AppSelect
            v-if="chat.ragEnabled"
            class="kb-select"
            look="chip"
            size="sm"
            :model-value="chat.selectedKbId"
            :options="kbOptions"
            placeholder="选择知识库"
            @update:model-value="onKbChange"
          />
          <span v-else-if="selectedKbName" class="kb-pending">知识库：{{ selectedKbName }}</span>
        </div>

        <div class="composer__send">
          <button
            v-if="chat.streaming"
            class="send-btn send-btn--stop"
            type="button"
            aria-label="停止生成"
            title="停止生成"
            @click="chat.stop()"
          >
            <Icon name="stop" :size="15" />
          </button>
          <button
            v-else
            class="send-btn"
            type="button"
            aria-label="发送消息"
            title="发送（Ctrl + Enter）"
            :disabled="!canSend()"
            @click="doSend"
          >
            <Icon name="send" :size="17" />
          </button>
        </div>
      </div>
    </div>

    <p class="composer-hint">
      内容由本地模型生成，请注意甄别 ·
      <template v-if="chat.streaming">生成中…</template>
      <template v-else>Ctrl + Enter 发送</template>
    </p>

    <input
      ref="fileInputRef"
      type="file"
      multiple
      hidden
      aria-label="选择附件文件"
      @change="onFilesChosen"
    >
  </div>
</template>

<style scoped>
.composer-wrap {
  position: relative;
}

/* ============ 输入台 ============ */

.composer {
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-pop);
  transition: border-color 0.15s ease-out;
}

.composer.is-focused {
  border-color: var(--accent-tint-line);
}

.composer__input {
  display: block;
  width: 100%;
  min-height: 46px;
  max-height: 190px;
  padding: 13px 17px 4px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--ink);
  background: transparent;
  border: none;
  outline: none;
}

.composer__input::placeholder {
  color: var(--ink-faint);
}

.composer__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 9px 9px 11px;
}

.composer__tools {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.tool-btn {
  position: relative;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  color: var(--ink-3);
  transition:
    background-color 0.14s ease-out,
    color 0.14s ease-out;
}

.tool-btn:hover,
.tool-btn.is-on {
  background: var(--accent-soft);
  color: var(--accent-text);
}

.tool-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 600;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
}

.rag-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 550;
  letter-spacing: 0.02em;
  color: var(--ink-3);
  border: 1px solid var(--line-strong);
  transition:
    all 0.15s ease-out;
}

.rag-toggle:hover {
  border-color: var(--accent-tint-line);
  color: var(--ink);
}

.rag-toggle.is-on {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.kb-select {
  max-width: 220px;
}

.kb-pending {
  font-size: 12.5px;
  color: var(--ink-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.send-btn {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--accent);
  color: #fff;
  transition:
    background-color 0.15s ease-out,
    transform 0.12s ease-out,
    opacity 0.15s ease-out;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.94);
}

.send-btn:disabled {
  opacity: 0.35;
}

.send-btn--stop {
  background: var(--btn-solid-bg);
  color: var(--btn-solid-fg);
}

.send-btn--stop:hover {
  background: var(--btn-solid-bg-hover);
}

.composer-hint {
  margin-top: 8px;
  text-align: center;
  font-size: 12px;
  color: var(--ink-faint);
}

/* ============ 附件面板 ============ */

.attach-panel {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 0;
  width: min(380px, calc(100vw - 48px));
  z-index: 40;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-pop);
  padding: 14px 15px 13px;
}

.attach-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink);
}

.attach-clear {
  font-size: 12px;
  color: var(--danger);
  padding: 2px 8px;
  border-radius: 6px;
}

.attach-clear:hover {
  background: var(--danger-soft);
}

.attach-panel__hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ink-3);
}

.attach-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 200px;
  overflow-y: auto;
}

.attach-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  color: var(--ink-2);
}

.attach-item:hover {
  background: var(--surface-well);
}

.attach-item__name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attach-item__size {
  font-size: 11.5px;
  color: var(--ink-faint);
  flex-shrink: 0;
}

.attach-item__del {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  color: var(--ink-faint);
  opacity: 0;
  transition:
    opacity 0.12s ease-out,
    color 0.12s ease-out;
}

.attach-item:hover .attach-item__del {
  opacity: 1;
}

.attach-item__del:hover {
  color: var(--danger);
}

.attach-empty {
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--ink-faint);
  text-align: center;
  padding: 8px 0;
}

.attach-add {
  margin-top: 10px;
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  font-size: 13px;
  color: var(--accent-text);
  border: 1px dashed var(--line-strong);
  border-radius: 9px;
  transition:
    border-color 0.14s ease-out,
    background-color 0.14s ease-out;
}

.attach-add:hover {
  border-color: var(--accent-tint-line);
  background: var(--accent-soft);
}
</style>

