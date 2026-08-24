<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ChatReference } from '@/types/api'
import { useKbStore } from '@/stores/kb'
import Icon from '@/ui/Icon.vue'

const props = defineProps<{ references: ChatReference[] }>()

const expanded = ref(false)
const kbStore = useKbStore()

const fileMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  for (const f of kbStore.detail?.files ?? []) {
    if (f.kb_file_id) map[f.kb_file_id] = f.filename
  }
  return map
})

function sourceName(refItem: ChatReference): string {
  return fileMap.value[refItem.file_id] ?? `片段 #${refItem.chunk_id}`
}

function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`
}
</script>

<template>
  <div class="refs">
    <button class="refs__toggle" type="button" :aria-expanded="expanded" @click="expanded = !expanded">
      <Icon name="library" :size="14" />
      <span>参考来源 · {{ references.length }}</span>
      <Icon name="chevron-down" :size="13" class="refs__caret" :class="{ 'is-open': expanded }" />
    </button>

    <ul v-if="expanded" class="refs__list">
      <li v-for="(r, i) in references" :key="`${r.file_id}-${r.chunk_id}`" class="ref-card">
        <div class="ref-card__head">
          <span class="ref-card__index tabular">{{ i + 1 }}</span>
          <span class="ref-card__name">{{ sourceName(r) }}</span>
          <span class="ref-card__score tabular" :title="`相似度 ${r.score.toFixed(3)}`">
            {{ scorePct(r.score) }}
          </span>
        </div>
        <p class="ref-card__preview">{{ r.content_preview }}</p>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.refs {
  margin-top: 12px;
}

.refs__toggle {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: var(--ink-2);
  padding: 5px 11px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface-well);
  transition:
    border-color 0.15s ease-out,
    color 0.15s ease-out;
}

.refs__toggle:hover {
  border-color: var(--accent-tint-line);
  color: var(--ink);
}

.refs__caret {
  transition: transform 0.16s ease-out;
}

.refs__caret.is-open {
  transform: rotate(180deg);
}

.refs__list {
  list-style: none;
  margin: 9px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.ref-card {
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: var(--r-md);
  padding: 10px 13px;
}

.ref-card__head {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.ref-card__index {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  font-size: 11.5px;
  border-radius: 6px;
  background: var(--accent-soft);
  color: var(--accent-text);
}

.ref-card__name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 550;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ref-card__score {
  font-size: 11.5px;
  color: var(--ink-3);
  flex-shrink: 0;
}

.ref-card__preview {
  margin-top: 6px;
  font-size: 12.8px;
  line-height: 1.62;
  color: var(--ink-2);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
