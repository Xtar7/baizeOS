<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import Icon from '@/ui/Icon.vue'

const chat = useChatStore()

function pick(id: string) {
  if (id === chat.chatId) return
  void chat.switchConversation(id)
}

async function removeOne(ev: MouseEvent, id: string) {
  ev.stopPropagation()
  if (!confirm('删除该对话？此操作不可撤销。')) return
  await chat.deleteConversation(id)
}

function fmtTime(ms: number) {
  const d = new Date(ms)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  return sameDay
    ? d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<template>
  <section class="cl" aria-label="对话列表">
    <header class="cl__head">
      <span class="cl__title">对话</span>
      <button
        class="cl__new"
        type="button"
        aria-label="新建对话"
        @click="chat.newChat()"
      >
        <Icon name="plus" :size="13" />
      </button>
    </header>

    <div v-if="chat.conversationsLoading" class="cl__hint">加载中…</div>
    <div v-else-if="!chat.conversations.length" class="cl__hint">还没有对话</div>

    <ul v-else class="cl__list">
      <li
        v-for="c in chat.conversations"
        :key="c.id"
        class="cl__item"
        :class="{ 'is-active': c.id === chat.chatId }"
        @click="pick(c.id)"
      >
        <span class="cl__name" :title="c.title || '未命名对话'">
          {{ c.title || '未命名对话' }}
        </span>
        <span class="cl__meta">
          {{ c.message_count }} · {{ fmtTime(c.updated_at) }}
        </span>
        <button
          class="cl__del"
          type="button"
          aria-label="删除"
          @click="removeOne($event, c.id)"
        >
          <Icon name="x" :size="12" />
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.cl {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 4px 8px 8px;
}
.cl__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 6px 8px;
  font-size: 12px;
  color: var(--ink-3);
  letter-spacing: 0.04em;
}
.cl__new {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--ink-2);
  cursor: pointer;
}
.cl__new:hover {
  color: var(--accent-text);
  border-color: var(--accent-tint-line);
}
.cl__hint {
  padding: 10px 6px;
  font-size: 12px;
  color: var(--ink-3);
}
.cl__list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  min-height: 0;
}
.cl__item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 8px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--ink-2);
  transition: background-color 0.14s ease-out, color 0.14s ease-out;
}
.cl__item:hover {
  background: rgb(28 25 23 / 5%);
}
.dark .cl__item:hover {
  background: rgb(255 255 255 / 5%);
}
.cl__item.is-active {
  background: var(--surface);
  color: var(--ink);
  box-shadow:
    inset 0 0 0 1px var(--line-strong),
    0 1px 2px rgb(28 25 23 / 4%);
}
.cl__name {
  grid-column: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cl__meta {
  grid-column: 1;
  font-size: 11px;
  color: var(--ink-3);
}
.cl__del {
  grid-column: 2;
  grid-row: 1 / span 2;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--ink-3);
  opacity: 0;
  cursor: pointer;
  transition:
    opacity 0.14s ease-out,
    color 0.14s ease-out;
}
.cl__item:hover .cl__del {
  opacity: 1;
}
.cl__del:hover {
  color: var(--accent-text);
}
</style>
