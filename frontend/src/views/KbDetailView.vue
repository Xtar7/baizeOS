<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useKbStore } from '@/stores/kb'
import { useSettingsStore } from '@/stores/settings'
import { uploadToKB, deleteKBFiles } from '@/api/kb'
import { ApiError } from '@/api/request'
import type { KnowledgeBase } from '@/types/api'
import Icon from '@/ui/Icon.vue'
import AppButton from '@/ui/AppButton.vue'
import EmptyState from '@/ui/EmptyState.vue'
import KbFormModal from '@/components/kb/KbFormModal.vue'
import { extOf, formatBytes, formatDate } from '@/utils/format'

const props = defineProps<{ kbId: string }>()

const router = useRouter()
const kbStore = useKbStore()
const settings = useSettingsStore()

// ============ 加载与头部 ============
onMounted(() => {
  void kbStore.fetchDetail(props.kbId).catch((err) => {
    settings.toast(err instanceof ApiError ? err.message : '加载知识库失败', 'error')
  })
  void kbStore.fetchEmbeddingModels().catch(() => undefined)
})

const kb = computed(() => kbStore.detail)

/** 切换过 embedding 模型但未重建：embedding_model 与 last_embedding_model 不一致 */
const needsRebuild = computed(() => {
  const k = kb.value
  if (!k?.last_embedding_model) return false
  return k.embedding_model !== k.last_embedding_model
})

const rebuildReason = computed(
  () =>
    `嵌入模型已从「${kb.value?.last_embedding_model}」切换为「${kb.value?.embedding_model}」，需要重建向量索引后才能生效。`,
)

// ============ 编辑 / 删除 ============
const editOpen = ref(false)

async function deleteKb() {
  if (!kb.value) return
  const ok = await settings.confirm({
    title: `删除知识库「${kb.value.display_name}」？`,
    body: '将同时删除其中的全部文件与向量索引，此操作不可恢复。',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await kbStore.remove(kb.value.kb_id)
    settings.toast('知识库已删除', 'success')
    void router.push('/kb')
  } catch (err) {
    settings.toast(err instanceof ApiError ? err.message : '删除失败', 'error')
  }
}

// ============ 重建索引 ============
const rebuilding = ref(false)

async function rebuild(force = true) {
  if (!kb.value || rebuilding.value) return
  rebuilding.value = true
  try {
    const res = await kbStore.reindex(kb.value.kb_id, force)
    if (res.status === 'skipped') {
      settings.toast(res.message || '当前模型一致，无需重建', 'info')
    } else {
      settings.toast(
        `重建完成：${res.ingested_files} 个文件 · ${res.chunks} 个分块`,
        'success',
      )
    }
    await kbStore.fetchDetail(kb.value.kb_id)
  } catch (err) {
    settings.toast(err instanceof ApiError ? err.message : '重建失败，请检查后端日志', 'error')
  } finally {
    rebuilding.value = false
  }
}

// ============ 上传 ============
const ACCEPT = '.txt,.md,.pdf'
const fileInputRef = ref<HTMLInputElement | null>(null)
let dragDepth = 0
const dragging = ref(false)

interface UploadTask {
  id: number
  name: string
  percent: number
  status: 'uploading' | 'done' | 'failed'
}

const queue = ref<UploadTask[]>([])
let taskSeq = 0

function pickFiles() {
  fileInputRef.value?.click()
}

async function handleFiles(files: File[]) {
  if (!files.length || !kb.value) return
  let okCount = 0
  const failedNames: string[] = []

  for (const f of files) {
    const task: UploadTask = {
      id: ++taskSeq,
      name: f.name,
      percent: 0,
      status: 'uploading',
    }
    queue.value.push(task)
    try {
      await uploadToKB(kb.value.kb_id, f, (p) => {
        task.percent = p
      })
      task.status = 'done'
      okCount++
    } catch (err) {
      task.status = 'failed'
      failedNames.push(f.name)
      console.error('上传失败', err)
    }
  }

  await kbStore.fetchDetail(kb.value.kb_id)
  void kbStore.fetchList(true).catch(() => undefined)

  if (okCount && !failedNames.length) settings.toast(`已上传 ${okCount} 个文件并向量化`, 'success')
  else if (okCount) settings.toast(`${okCount} 个成功，${failedNames.length} 个失败`, 'info')
  else settings.toast(`上传失败：仅支持 .txt / .md / .pdf 格式`, 'error')

  // 已完成的任务稍后自动移出队列
  window.setTimeout(() => {
    queue.value = queue.value.filter((t) => t.status === 'uploading')
  }, 3500)
}

function onInputChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  void handleFiles(files)
}

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

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragDepth = 0
  dragging.value = false
  void handleFiles(Array.from(e.dataTransfer?.files ?? []))
}

// ============ 文件选择与删除 ============
const selected = ref<Set<string>>(new Set())
const files = computed(() => kb.value?.files ?? [])

const selectedCount = computed(() => selected.value.size)
const allSelected = computed(() => files.value.length > 0 && selected.value.size === files.value.length)

function toggleAll() {
  selected.value = allSelected.value ? new Set() : new Set(files.value.map((f) => f.kb_file_id))
}

function toggleOne(id: string) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

async function removeOne(fileId: string, filename: string) {
  const ok = await settings.confirm({
    title: `删除文件「${filename}」？`,
    body: '将从知识库中移除该文件及其向量分块。',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  await doDelete([fileId])
}

async function removeSelected() {
  const ids = [...selected.value]
  const ok = await settings.confirm({
    title: `删除选中的 ${ids.length} 个文件？`,
    body: '将从知识库中移除这些文件及其向量分块。',
    confirmText: '批量删除',
    danger: true,
  })
  if (!ok) return
  await doDelete(ids)
}

async function doDelete(ids: string[]) {
  if (!kb.value) return
  try {
    await deleteKBFiles(kb.value.kb_id, ids)
    settings.toast(`已删除 ${ids.length} 个文件`, 'success')
    selected.value = new Set()
    await kbStore.fetchDetail(kb.value.kb_id)
    void kbStore.fetchList(true).catch(() => undefined)
  } catch (err) {
    settings.toast(err instanceof ApiError ? err.message : '删除失败', 'error')
  }
}

const FILE_ICON: Record<string, string> = {
  md: 'file',
  txt: 'file',
  pdf: 'file',
}
</script>

<template>
  <div
    class="page"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- 返回 -->
    <RouterLink to="/kb" class="back">
      <Icon name="arrow-left" :size="15" />
      返回列表
    </RouterLink>

    <!-- 加载中 -->
    <div v-if="kbStore.loadingDetail && !kb" class="loading">加载中…</div>

    <template v-else-if="kb">
      <!-- 头部 -->
      <header class="head">
        <div class="head__text">
          <h1 class="head__title">{{ kb.display_name }}</h1>
          <p v-if="kb.description" class="head__desc">{{ kb.description }}</p>
          <div class="head__meta">
            <span class="meta-chip"><Icon name="cpu" :size="12.5" />{{ kb.embedding_model || '未设置模型' }}<template v-if="kb.embedding_dim"> · {{ kb.embedding_dim }} 维</template></span>
            <span class="meta-chip tabular"><Icon name="file" :size="12.5" />{{ files.length }} 个文件</span>
            <span class="meta-chip tabular"><Icon name="rebuild" :size="12.5" />创建于 {{ formatDate(kb.created_at) }}</span>
          </div>
        </div>

        <div class="head__actions">
          <AppButton variant="solid" size="md" @click="pickFiles">
            <template #icon><Icon name="upload" :size="15" /></template>
            上传文件
          </AppButton>
          <AppButton variant="soft" size="md" :loading="rebuilding" @click="rebuild(true)">
            <template #icon><Icon name="rebuild" :size="15" /></template>
            重建索引
          </AppButton>
          <AppButton variant="ghost" size="md" @click="editOpen = true">
            <template #icon><Icon name="edit" :size="14.5" /></template>
            编辑
          </AppButton>
          <AppButton variant="danger" size="md" @click="deleteKb">
            <template #icon><Icon name="trash" :size="14.5" /></template>
            删除
          </AppButton>
        </div>
      </header>

      <!-- 重建提醒横幅 -->
      <Transition name="pop">
        <div v-if="needsRebuild" class="rebuild-banner" role="alert">
          <Icon name="alert" :size="16" />
          <p>{{ rebuildReason }}</p>
          <AppButton variant="danger" size="sm" :loading="rebuilding" @click="rebuild(true)">
            立即重建
          </AppButton>
        </div>
      </Transition>

      <!-- 上传进度队列 -->
      <TransitionGroup v-if="queue.length" name="pop" tag="ul" class="queue">
        <li v-for="t in queue" :key="t.id" class="queue-item">
          <span class="queue-item__name">{{ t.name }}</span>
          <div v-if="t.status === 'uploading'" class="queue-item__bar">
            <div class="queue-item__fill" :style="{ width: `${t.percent}%` }" />
          </div>
          <span v-else class="queue-item__state" :class="t.status === 'done' ? 'is-done' : 'is-failed'">
            {{ t.status === 'done' ? '完成' : '失败' }}
          </span>
        </li>
      </TransitionGroup>

      <!-- 批量操作条 -->
      <Transition name="pop">
        <div v-if="selectedCount > 0" class="bulk-bar">
          <span class="tabular">已选择 {{ selectedCount }} 项</span>
          <div class="bulk-bar__btns">
            <AppButton variant="ghost" size="sm" @click="selected = new Set()">取消</AppButton>
            <AppButton variant="danger" size="sm" @click="removeSelected">
              <template #icon><Icon name="trash" :size="13.5" /></template>
              批量删除
            </AppButton>
          </div>
        </div>
      </Transition>

      <!-- 文件列表 -->
      <section class="files">
        <EmptyState
          v-if="!files.length"
          icon="file"
          title="还没有文档"
          hint="把 .txt、.md 或 .pdf 文件拖到这里，或点击右上角「上传文件」。上传后会自动解析、切分并建立向量索引。"
        >
          <AppButton variant="solid" size="md" @click="pickFiles">
            <template #icon><Icon name="plus" :size="15" /></template>
            上传第一个文件
          </AppButton>
        </EmptyState>

        <template v-else>
          <div class="files-toolbar">
            <label class="check-all">
              <input
                type="checkbox"
                :checked="allSelected"
                aria-label="全选文件"
                @change="toggleAll"
              >
              文件名
            </label>
          </div>

          <ul class="file-list">
            <li
              v-for="f in files"
              :key="f.kb_file_id"
              class="file-row"
              :class="{ 'is-selected': selected.has(f.kb_file_id) }"
            >
              <input
                type="checkbox"
                class="file-row__check"
                :checked="selected.has(f.kb_file_id)"
                :aria-label="`选择 ${f.filename}`"
                @change="toggleOne(f.kb_file_id)"
              >
              <Icon :name="FILE_ICON[extOf(f.filename)] ?? 'file'" :size="16" class="file-row__icon" />
              <span class="file-row__name" :title="f.filename">{{ f.filename }}</span>
              <span class="file-row__size tabular">{{ formatBytes(f.bytes) }}</span>
              <span class="file-row__date tabular">{{ formatDate(f.created_at) }}</span>
              <button
                class="icon-btn"
                type="button"
                :aria-label="`删除 ${f.filename}`"
                title="删除"
                @click="removeOne(f.kb_file_id, f.filename)"
              >
                <Icon name="trash" :size="14" />
              </button>
            </li>
          </ul>
        </template>
      </section>
    </template>

    <input
      ref="fileInputRef"
      type="file"
      multiple
      :accept="ACCEPT"
      hidden
      aria-label="选择要上传的文件"
      @change="onInputChosen"
    >

    <!-- 拖拽遮罩 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="dragging" class="drop-overlay">
          <div class="drop-card">
            <Icon name="upload" :size="26" />
            <p>松开以解析并索引这些文件</p>
            <span class="drop-card__hint">支持 .txt · .md · .pdf</span>
          </div>
        </div>
      </Transition>
    </Teleport>

    <KbFormModal
      v-model:open="editOpen"
      :editing="kb as KnowledgeBase | null"
      @saved="() => kb && void kbStore.fetchDetail(kb.kb_id)"
    />
  </div>
</template>

<style scoped>
.page {
  max-width: 920px;
  margin: 0 auto;
  padding: 26px clamp(16px, 2.9vw, 28px) 56px;
}

.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ink-3);
  margin-bottom: 18px;
  border-radius: 6px;
}

.back:hover {
  color: var(--accent-text);
  text-decoration: none;
}

.loading {
  padding: 60px 0;
  text-align: center;
  color: var(--ink-3);
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.head__title {
  font-size: 22px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.head__desc {
  margin-top: 4px;
  font-size: 13.5px;
  color: var(--ink-2);
}

.head__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--ink-3);
  background: var(--surface-well);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 10px;
  max-width: 300px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.head__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

/* 横幅 */
.rebuild-banner {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 12px 15px;
  border: 1px solid var(--warn-line);
  background: var(--warn-soft);
  border-radius: var(--r-md);
  color: var(--warn);
  margin-bottom: 16px;
  font-size: 13.5px;
}

.rebuild-banner svg {
  flex-shrink: 0;
}

.rebuild-banner p {
  flex: 1;
}

/* 上传队列 */
.queue {
  list-style: none;
  margin: 0 0 14px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.queue-item__name {
  width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink-2);
  flex-shrink: 0;
}

.queue-item__bar {
  flex: 1;
  height: 5px;
  border-radius: 999px;
  background: var(--surface-well);
  overflow: hidden;
}

.queue-item__fill {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
  transition: width 0.25s ease-out;
}

.queue-item__state.is-done {
  color: var(--ok);
  font-size: 12.5px;
}

.queue-item__state.is-failed {
  color: var(--danger);
  font-size: 12.5px;
}

/* 批量条 */
.bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 8px 8px 15px;
  margin-bottom: 12px;
  border: 1px solid var(--accent-tint-line);
  background: var(--accent-soft);
  border-radius: var(--r-md);
  font-size: 13px;
  color: var(--ink);
}

.bulk-bar__btns {
  display: flex;
  gap: 6px;
}

/* 文件区 */
.files {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  overflow: hidden;
}

.files-toolbar {
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
}

.check-all {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
  color: var(--ink-3);
  cursor: pointer;
}

.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 16px;
  transition: background-color 0.12s ease-out;
}

.file-row:hover {
  background: var(--surface-well);
}

.file-row.is-selected {
  background: var(--accent-soft);
}

.file-row + .file-row {
  border-top: 1px solid var(--line);
}

.file-row input[type='checkbox'] {
  accent-color: var(--accent);
  width: 15px;
  height: 15px;
  cursor: pointer;
  flex-shrink: 0;
}

.file-row__icon {
  color: var(--ink-faint);
  flex-shrink: 0;
}

.file-row__name {
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-row__size {
  width: 76px;
  text-align: right;
  font-size: 12.5px;
  color: var(--ink-3);
  flex-shrink: 0;
}

.file-row__date {
  width: 92px;
  text-align: right;
  font-size: 12.5px;
  color: var(--ink-3);
  flex-shrink: 0;
}

.icon-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--ink-faint);
  opacity: 0;
  transition:
    opacity 0.13s ease-out,
    background-color 0.13s ease-out,
    color 0.13s ease-out;
}

.file-row:hover .icon-btn,
.icon-btn:focus-visible {
  opacity: 1;
}

.icon-btn:hover {
  background: var(--danger-soft);
  color: var(--danger);
}

@media (max-width: 640px) {
  .file-row__date,
  .file-row__size {
    display: none;
  }

  .head__actions {
    width: 100%;
  }
}

/* 遮罩 */
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
  gap: 8px;
  padding: 34px 52px;
  border: 2px dashed var(--accent-tint-line);
  border-radius: var(--r-lg);
  background: var(--surface);
  color: var(--accent-text);
  font-size: 14.5px;
  box-shadow: var(--shadow-modal);
  text-align: center;
}

.drop-card__hint {
  font-size: 12px;
  color: var(--ink-3);
}
</style>
