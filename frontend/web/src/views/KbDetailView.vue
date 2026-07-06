<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useKbStore } from '@/stores/kb'
import { useSettingsStore } from '@/stores/settings'
import * as kbApi from '@/api/kb'

const route = useRoute()
const router = useRouter()
const kbStore = useKbStore()

const kbId = route.params.id as string
const uploading = ref(false)
const reindexing = ref(false)

onMounted(async () => {
  await kbStore.fetchDetail(kbId)
})

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || !kbStore.current) return

  uploading.value = true
  try {
    await kbApi.uploadToKB(kbStore.current.kb_id, file)
    await kbStore.fetchDetail(kbId)
    useSettingsStore().showToast('文件上传成功', 'success')
  } catch (e: unknown) {
    const err = e as { message?: string }
    useSettingsStore().showToast(`上传失败: ${err.message}`, 'error')
  } finally {
    uploading.value = false
    target.value = ''
  }
}

async function handleReindex() {
  if (!kbStore.current) return
  reindexing.value = true
  try {
    const res = await kbApi.reindexKB(kbId, true)
    const data = res.data
    if (data.status === 'completed') {
      useSettingsStore().showToast(`重建完成: ${data.chunks} 个 chunks`, 'success')
    } else {
      useSettingsStore().showToast(data.status, 'info')
    }
    await kbStore.fetchDetail(kbId)
  } catch (e: unknown) {
    useSettingsStore().showToast('重建失败', 'error')
  } finally {
    reindexing.value = false
  }
}

async function handleDeleteKB() {
  if (!kbStore.current || !confirm(`确定删除 "${kbStore.current.display_name}" 吗？`)) return
  try {
    await kbStore.remove(kbId)
    router.push('/knowledge')
    useSettingsStore().showToast('知识库已删除', 'success')
  } catch {
    useSettingsStore().showToast('删除失败', 'error')
  }
}

function goBack() {
  router.push('/knowledge')
}
</script>

<template>
  <div class="kb-detail">
    <!-- Header -->
    <div class="kb-detail-header">
      <button class="btn-back" @click="goBack">← 返回</button>
      <div class="kb-info">
        <h2 v-if="kbStore.current">{{ kbStore.current.display_name }}</h2>
        <p v-if="kbStore.current">{{ kbStore.current.description || '暂无描述' }}</p>
      </div>
      <div class="kb-actions">
        <button class="btn-reindex" :disabled="reindexing" @click="handleReindex">
          {{ reindexing ? '重建中...' : '🔄 重建索引' }}
        </button>
        <button class="btn-delete" @click="handleDeleteKB">🗑 删除</button>
      </div>
    </div>

    <div class="kb-detail-body" v-if="kbStore.current">
      <!-- File list -->
      <div class="kb-section">
        <div class="section-header">
          <h3>文件列表（{{ kbStore.current.files?.length || 0 }}）</h3>
          <label class="btn-upload">
            ＋ 上传文件
            <input type="file" accept=".txt,.md,.pdf" @change="handleFileUpload" hidden />
          </label>
        </div>

        <div v-if="!kbStore.current.files?.length" class="empty-files">
          暂无文件，上传文档开始构建知识库
        </div>

        <div v-else class="file-list">
          <div v-for="f in kbStore.current.files" :key="f.kb_file_id" class="file-item">
            <span class="file-name">{{ f.filename }}</span>
            <span class="file-meta">
              {{ (f.bytes / 1024).toFixed(1) }} KB · {{ new Date(f.created_at).toLocaleDateString() }}
            </span>
          </div>
        </div>
      </div>

      <!-- Meta info -->
      <div class="kb-section">
        <h3>知识库信息</h3>
        <div class="meta-grid">
          <div class="meta-item">
            <span class="meta-label">Embedding 模型</span>
            <span class="meta-value">{{ kbStore.current.embedding_model }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">向量维度</span>
            <span class="meta-value">{{ kbStore.current.embedding_dim }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">系统提示词</span>
            <span class="meta-value">{{ kbStore.current.system_prompt || '无' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">创建时间</span>
            <span class="meta-value">{{ new Date(kbStore.current.created_at).toLocaleString() }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="kbStore.loading" class="loading">加载中...</div>
  </div>
</template>

<style scoped>
.kb-detail {
  max-width: 700px;
  margin: 0 auto;
  width: 100%;
}

.kb-detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.btn-back {
  background: none;
  border: none;
  color: var(--accent);
  font-size: 14px;
  cursor: pointer;
  padding: 6px 0;
}

.btn-back:hover {
  text-decoration: underline;
}

.kb-info h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}

.kb-info p {
  font-size: 13px;
  color: var(--text-secondary);
}

.kb-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.btn-reindex {
  padding: 7px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
}

.btn-reindex:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-delete {
  padding: 7px 14px;
  border: 1px solid rgba(255, 59, 48, 0.3);
  border-radius: 8px;
  background: transparent;
  color: #ff3b30;
  font-size: 13px;
  cursor: pointer;
}

.kb-section {
  margin-bottom: 28px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-upload {
  padding: 7px 14px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-upload:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.empty-files {
  text-align: center;
  padding: 32px;
  color: var(--text-tertiary);
  font-size: 14px;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-primary);
}

.file-name {
  font-size: 14px;
  color: var(--text-primary);
}

.file-meta {
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.meta-item {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-primary);
}

.meta-label {
  display: block;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.meta-value {
  font-size: 14px;
  color: var(--text-primary);
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
