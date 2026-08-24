<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listModels } from '@/api/model'
import { useKbStore } from '@/stores/kb'
import { useSettingsStore } from '@/stores/settings'
import type { LlmModel } from '@/types/api'
import Icon from '@/ui/Icon.vue'
import { formatDate } from '@/utils/format'

const kbStore = useKbStore()
const settings = useSettingsStore()

const llmModels = ref<LlmModel[]>([])
const loadingLlm = ref(false)

onMounted(async () => {
  void kbStore.fetchEmbeddingModels().catch(() => undefined)
  loadingLlm.value = true
  try {
    const res = await listModels()
    llmModels.value = res.data ?? []
  } catch {
    /* 后端未启动时静默，列表显示空态 */
  } finally {
    loadingLlm.value = false
  }
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h1 class="page-title">设置</h1>
      <p class="page-sub">模型、外观与本机服务信息</p>
    </header>

    <!-- 模型服务 -->
    <section class="section">
      <h2 class="section__title"><Icon name="cpu" :size="16" /> 模型服务</h2>

      <div class="panel">
        <h3 class="panel__head">本地 LLM（GGUF）</h3>
        <p v-if="loadingLlm" class="muted">加载中…</p>
        <p v-else-if="!llmModels.length" class="muted">后端未返回模型列表 —— 请确认服务已在 localhost:5000 启动。</p>
        <ul v-else class="model-list">
          <li v-for="m in llmModels" :key="m.id" class="model-row">
            <span class="mono model-row__id">{{ m.id }}</span>
            <span class="badge">{{ m.owned_by === 'local' ? '本地' : m.owned_by }}</span>
            <span v-if="llmModels.length" class="model-row__date tabular">{{ formatDate(new Date(m.created * 1000).toISOString()) }}</span>
          </li>
        </ul>
        <p class="panel__note">对话请求默认使用后端配置的 default 模型。</p>
      </div>

      <div class="panel">
        <h3 class="panel__head">Embedding 模型</h3>
        <p v-if="kbStore.modelsLoading && !kbStore.embeddingModels.length" class="muted">加载中…</p>
        <p v-else-if="!kbStore.embeddingModels.length" class="muted">暂无可用嵌入模型。</p>
        <ul v-else class="model-list">
          <li v-for="m in kbStore.embeddingModels" :key="m.name" class="model-row">
            <span class="mono model-row__id">{{ m.name }}</span>
            <span class="badge badge--dim tabular">{{ m.dim }} 维</span>
            <span v-if="m.is_default || m.name === kbStore.defaultEmbedding" class="badge badge--accent">默认</span>
          </li>
        </ul>
        <p class="panel__note">在知识库编辑中切换嵌入模型后，需重建该库的向量索引。</p>
      </div>
    </section>

    <!-- 外观 -->
    <section class="section">
      <h2 class="section__title"><Icon name="sun" :size="16" /> 外观</h2>
      <div class="panel">
        <div class="theme-row">
          <span>界面主题</span>
          <div class="segmented" role="radiogroup" aria-label="界面主题">
            <button
              class="seg"
              role="radio"
              :aria-checked="settings.theme === 'light'"
              :class="{ 'is-on': settings.theme === 'light' }"
              @click="settings.theme = 'light'"
            >
              浅色
            </button>
            <button
              class="seg"
              role="radio"
              :aria-checked="settings.theme === 'dark'"
              :class="{ 'is-on': settings.theme === 'dark' }"
              @click="settings.theme = 'dark'"
            >
              深色
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 关于 -->
    <section class="section">
      <h2 class="section__title"><Icon name="spark" :size="16" /> 关于</h2>
      <div class="panel about">
        <div class="brand-line">
          <span class="brand-mark"><Icon name="spark" :size="15" :stroke-width="2" /></span>
          <span class="brand-name">baize<i>OS</i></span>
        </div>
        <dl class="about-grid">
          <dt>版本</dt>
          <dd>v1.0.0</dd>
          <dt>后端地址</dt>
          <dd class="mono">{{ settings.backendHint }}</dd>
          <dt>定位</dt>
          <dd>基于本地大模型的 RAG 知识库问答系统</dd>
        </dl>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page {
  max-width: 760px;
  margin: 0 auto;
  padding: 30px clamp(16px, 2.9vw, 28px) 56px;
}

.page-head {
  margin-bottom: 24px;
}

.page-title {
  font-size: 23px;
  font-weight: 650;
}

.page-sub {
  margin-top: 3px;
  font-size: 13.5px;
  color: var(--ink-3);
}

.section {
  margin-bottom: 30px;
}

.section__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-2);
  margin-bottom: 11px;
}

.section__title svg {
  color: var(--accent-text);
}

.panel {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  padding: 16px 18px;
}

.panel + .panel {
  margin-top: 12px;
}

.panel__head {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 10px;
}

.panel__note {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 12.5px;
  color: var(--ink-3);
}

.muted {
  font-size: 13px;
  color: var(--ink-faint);
  padding: 6px 0;
}

.model-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.model-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.model-row + .model-row {
  border-top: 1px solid var(--line);
}

.mono {
  font-family: var(--font-mono);
}

.model-row__id {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-row__date {
  font-size: 12px;
  color: var(--ink-faint);
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-well);
  color: var(--ink-3);
  flex-shrink: 0;
}

.badge--dim {
  border: 1px solid var(--line);
}

.badge--accent {
  background: var(--accent-soft);
  color: var(--accent-text);
}

/* 外观 */
.theme-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  font-size: 14px;
}

.segmented {
  display: inline-flex;
  background: var(--surface-well);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 3px;
  gap: 2px;
}

.seg {
  height: 28px;
  padding: 0 16px;
  font-size: 13px;
  border-radius: 7px;
  color: var(--ink-3);
  transition:
    background-color 0.14s ease-out,
    color 0.14s ease-out,
    box-shadow 0.14s ease-out;
}

.seg:hover {
  color: var(--ink);
}

.seg.is-on {
  background: var(--surface);
  color: var(--ink);
  box-shadow:
    inset 0 0 0 1px var(--line-strong),
    0 1px 2px rgb(28 25 23 / 5%);
}

/* 关于 */
.brand-line {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 13px;
}

.brand-mark {
  width: 27px;
  height: 27px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: var(--accent);
  color: #fff;
}

.brand-name {
  font-family: var(--font-display);
  font-size: 17px;
  color: var(--ink);
}

.brand-name i {
  font-style: normal;
  color: var(--accent-text);
}

.about-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 7px 18px;
  margin: 0;
  font-size: 13px;
}

.about-grid dt {
  color: var(--ink-3);
}

.about-grid dd {
  margin: 0;
  color: var(--ink);
}
</style>
