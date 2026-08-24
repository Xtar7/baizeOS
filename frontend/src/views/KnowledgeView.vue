<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useKbStore } from '@/stores/kb'
import { useSettingsStore } from '@/stores/settings'
import { ApiError } from '@/api/request'
import type { KbListItem, KnowledgeBase } from '@/types/api'
import Icon from '@/ui/Icon.vue'
import AppButton from '@/ui/AppButton.vue'
import EmptyState from '@/ui/EmptyState.vue'
import KbFormModal from '@/components/kb/KbFormModal.vue'
import { fromNow } from '@/utils/format'

const router = useRouter()
const kbStore = useKbStore()
const settings = useSettingsStore()

const createOpen = ref(false)
const editTarget = ref<KbListItem | KnowledgeBase | null>(null)

onMounted(() => {
  void kbStore.fetchList(true).catch(() => undefined)
})

function openDetail(kb: KbListItem) {
  void router.push(`/kb/${kb.kb_id}`)
}

async function askEdit(kb: KbListItem) {
  // 编辑弹窗需要完整 meta（提示词、embedding 模型），先拉详情
  try {
    await kbStore.fetchDetail(kb.kb_id)
    editTarget.value = kbStore.detail
    createOpen.value = true
  } catch {
    settings.toast('获取知识库信息失败', 'error')
  }
}

async function askDelete(kb: KbListItem) {
  const ok = await settings.confirm({
    title: `删除知识库「${kb.display_name}」？`,
    body: '将同时删除其中的全部文件与向量索引，此操作不可恢复。',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await kbStore.remove(kb.kb_id)
    settings.toast(`已删除「${kb.display_name}」`, 'success')
  } catch (err) {
    settings.toast(err instanceof ApiError ? err.message : '删除失败', 'error')
  }
}
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="page-title">知识库</h1>
        <p class="page-sub tabular" v-if="kbStore.list.length">{{ kbStore.list.length }} 个知识库 · 上传文档构建专属问答</p>
        <p class="page-sub" v-else>上传文档，构建属于你的本地知识库</p>
      </div>
      <AppButton variant="solid" size="md" @click="createOpen = true; editTarget = null">
        <template #icon><Icon name="plus" :size="15" /></template>
        新建知识库
      </AppButton>
    </header>

    <!-- 加载骨架 -->
    <div v-if="kbStore.loadingList && !kbStore.list.length" class="grid">
      <div v-for="i in 4" :key="i" class="card card--skeleton" aria-hidden="true">
        <div class="sk sk--title" />
        <div class="sk sk--line" />
        <div class="sk sk--line sk--short" />
      </div>
    </div>

    <!-- 空状态 -->
    <EmptyState
      v-else-if="!kbStore.list.length"
      icon="library"
      title="还没有知识库"
      hint="创建一个知识库并上传 .txt / .md / .pdf 文档，即可在对话中引用这些内容。"
    >
      <AppButton variant="solid" size="md" @click="createOpen = true">
        <template #icon><Icon name="plus" :size="15" /></template>
        创建第一个知识库
      </AppButton>
    </EmptyState>

    <!-- 卡片网格 -->
    <div v-else class="grid">
      <article
        v-for="kb in kbStore.list"
        :key="kb.kb_id"
        class="card"
        tabindex="0"
        role="link"
        :aria-label="`打开知识库 ${kb.display_name}`"
        @click="openDetail(kb)"
        @keydown.enter="openDetail(kb)"
      >
        <div class="card__top">
          <span class="card__icon"><Icon name="library" :size="17" /></span>
          <div class="card__actions">
            <button class="icon-btn" type="button" aria-label="编辑" title="编辑" @click.stop="askEdit(kb)">
              <Icon name="edit" :size="14.5" />
            </button>
            <button class="icon-btn icon-btn--danger" type="button" aria-label="删除" title="删除" @click.stop="askDelete(kb)">
              <Icon name="trash" :size="14.5" />
            </button>
          </div>
        </div>

        <h2 class="card__name">{{ kb.display_name }}</h2>
        <p class="card__desc">{{ kb.description || '暂无描述' }}</p>

        <footer class="card__meta">
          <span class="meta-chip tabular"><Icon name="file" :size="12.5" />{{ kb.file_count }}</span>
          <span class="card__time tabular">{{ fromNow(kb.updated_at) }}</span>
        </footer>
      </article>
    </div>

    <KbFormModal
      v-model:open="createOpen"
      :editing="editTarget"
      @saved="() => void kbStore.fetchList(true).catch(() => undefined)"
    />
  </div>
</template>

<style scoped>
.page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 30px clamp(16px, 2.9vw, 28px) 48px;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.page-title {
  font-size: 23px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.page-sub {
  margin-top: 3px;
  font-size: 13.5px;
  color: var(--ink-3);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
  gap: 14px;
}

.card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  padding: 16px 17px 14px;
  cursor: pointer;
  transition:
    border-color 0.16s ease-out,
    transform 0.16s ease-out,
    box-shadow 0.16s ease-out;
}

.card:hover {
  border-color: var(--line-strong);
  transform: translateY(-2px);
  box-shadow: var(--shadow-pop);
}

.card:focus-visible {
  outline-offset: 3px;
}

.card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
}

.card__icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--accent-soft);
  color: var(--accent-text);
}

.card__actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.14s ease-out;
}

.card:hover .card__actions,
.card:focus-within .card__actions {
  opacity: 1;
}

.icon-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--ink-3);
}

.icon-btn:hover {
  background: var(--surface-well);
  color: var(--ink);
}

.icon-btn--danger:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.card__name {
  font-size: 15.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card__desc {
  margin-top: 5px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ink-3);
  min-height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card__meta {
  margin-top: 13px;
  padding-top: 11px;
  border-top: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--ink-3);
  background: var(--surface-well);
  border-radius: 999px;
  padding: 3px 9px;
}

.card__time {
  font-size: 12px;
  color: var(--ink-faint);
}

/* 骨架 */
.card--skeleton {
  cursor: default;
  pointer-events: none;
}

.sk {
  border-radius: 7px;
  background: linear-gradient(90deg, var(--surface-well) 25%, var(--bg-deep) 50%, var(--surface-well) 75%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.4s ease-in-out infinite;
}

@keyframes sk-shimmer {
  to {
    background-position: -200% 0;
  }
}

.sk--title {
  height: 18px;
  width: 55%;
  margin-bottom: 13px;
}

.sk--line {
  height: 12px;
  width: 100%;
  margin-top: 8px;
}

.sk--short {
  width: 62%;
}
</style>
