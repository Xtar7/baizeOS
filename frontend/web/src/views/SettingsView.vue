<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as modelApi from '@/api/model'

const llmModels = ref<any[]>([])
const embeddingModels = ref<any[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const [llmRes, embRes] = await Promise.allSettled([
      modelApi.listModels(),
      modelApi.listEmbeddingModels(),
    ])
    if (llmRes.status === 'fulfilled') llmModels.value = llmRes.value.data.data || []
    if (embRes.status === 'fulfilled') embeddingModels.value = embRes.value.data.models || []
  } catch {
    // silently ignore
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="settings-view">
    <h2>设置</h2>

    <div class="settings-section">
      <h3>LLM 模型</h3>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="llmModels.length === 0" class="empty">暂无数据，请先启动后端服务</div>
      <div v-else class="model-list">
        <div v-for="m in llmModels" :key="m.id" class="model-item">
          <span class="model-id">{{ m.id }}</span>
          <span class="model-owned">{{ m.owned_by }}</span>
        </div>
      </div>
    </div>

    <div class="settings-section">
      <h3>Embedding 模型</h3>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="embeddingModels.length === 0" class="empty">暂无数据</div>
      <div v-else class="model-list">
        <div v-for="m in embeddingModels" :key="m.name" class="model-item">
          <span class="model-id">{{ m.name }}</span>
          <span class="model-dim">dim: {{ m.dim }}</span>
          <span v-if="m.is_default" class="badge-default">默认</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 24px;
}

.settings-section {
  margin-bottom: 28px;
}

.settings-section h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.loading {
  color: var(--text-tertiary);
  text-align: center;
  padding: 20px;
}

.empty {
  color: var(--text-tertiary);
  text-align: center;
  padding: 20px;
  font-size: 14px;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-primary);
}

.model-id {
  font-size: 14px;
  color: var(--text-primary);
  font-family: var(--font-mono);
  flex: 1;
}

.model-dim {
  font-size: 12px;
  color: var(--text-tertiary);
}

.model-owned {
  font-size: 12px;
  color: var(--text-tertiary);
}

.badge-default {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--accent-light);
  color: var(--accent);
}
</style>
