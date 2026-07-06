<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useKbStore } from '@/stores/kb'
import { useSettingsStore } from '@/stores/settings'
import type { KBListItem } from '@/api/kb'

const router = useRouter()
const kbStore = useKbStore()
const settingsStore = useSettingsStore()

const showCreateModal = ref(false)
const newName = ref('')
const newDesc = ref('')
const newPrompt = ref('')

onMounted(() => {
  kbStore.fetchList()
})

async function handleCreate() {
  if (!newName.value.trim()) {
    settingsStore.showToast('请输入知识库名称', 'error')
    return
  }
  try {
    await kbStore.create({
      display_name: newName.value,
      description: newDesc.value,
      system_prompt: newPrompt.value,
    })
    showCreateModal.value = false
    newName.value = ''
    newDesc.value = ''
    newPrompt.value = ''
    await kbStore.fetchList()
    settingsStore.showToast('知识库创建成功', 'success')
  } catch (e: unknown) {
    const err = e as { message?: string }
    settingsStore.showToast(`创建失败: ${err.message}`, 'error')
  }
}

async function handleDelete(kb: KBListItem) {
  if (!confirm(`确定删除 "${kb.display_name}" 吗？`)) return
  try {
    await kbStore.remove(kb.kb_id)
    settingsStore.showToast('已删除', 'success')
  } catch (e: unknown) {
    settingsStore.showToast('删除失败', 'error')
  }
}

function goToDetail(kbId: string) {
  router.push(`/knowledge/${kbId}`)
}
</script>

<template>
  <div class="knowledge-view">
    <div class="kb-header">
      <h2>知识库管理</h2>
      <button class="btn-create" @click="showCreateModal = true">＋ 新建知识库</button>
    </div>

    <!-- Grid -->
    <div class="kb-grid">
      <div
        v-for="kb in kbStore.list"
        :key="kb.kb_id"
        class="kb-card"
        @click="goToDetail(kb.kb_id)"
      >
        <div class="kb-card-header">
          <h3>{{ kb.display_name }}</h3>
          <span class="kb-file-count">{{ kb.file_count }} 个文件</span>
        </div>
        <p class="kb-desc">{{ kb.description || '暂无描述' }}</p>
        <div class="kb-card-footer">
          <span class="kb-date">{{ new Date(kb.created_at).toLocaleDateString() }}</span>
          <button class="btn-delete-sm" @click.stop="handleDelete(kb)">删除</button>
        </div>
      </div>
    </div>

    <!-- Empty -->
    <div v-if="!kbStore.loading && kbStore.list.length === 0" class="kb-empty">
      <div class="kb-empty-icon">📚</div>
      <h3>还没有知识库</h3>
      <p>创建一个知识库来存储你的文档，开启 RAG 智能问答</p>
    </div>

    <!-- Loading -->
    <div v-if="kbStore.loading" class="kb-loading">加载中...</div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>新建知识库</h3>
        <div class="modal-form">
          <label>
            名称 <span class="required">*</span>
            <input v-model="newName" placeholder="例如：技术文档" />
          </label>
          <label>
            描述
            <input v-model="newDesc" placeholder="可选" />
          </label>
          <label>
            系统提示词
            <input v-model="newPrompt" placeholder="例如：你是一个专业助手" />
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showCreateModal = false">取消</button>
          <button class="btn-confirm" @click="handleCreate">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-view {
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.kb-header h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-create {
  padding: 8px 18px;
  border-radius: 8px;
  border: none;
  background: var(--accent);
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-create:hover {
  background: var(--accent-hover);
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.kb-card {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-primary);
  cursor: pointer;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.kb-card:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.kb-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.kb-card-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.kb-file-count {
  font-size: 12px;
  color: var(--text-tertiary);
}

.kb-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  line-height: 1.5;
}

.kb-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kb-date {
  font-size: 12px;
  color: var(--text-tertiary);
}

.btn-delete-sm {
  font-size: 12px;
  color: #ff3b30;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.btn-delete-sm:hover {
  background: rgba(255, 59, 48, 0.1);
}

.kb-empty {
  text-align: center;
  padding: 60px 20px;
}

.kb-empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.kb-empty h3 {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.kb-empty p {
  color: var(--text-secondary);
}

.kb-loading {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-primary);
  border-radius: 16px;
  padding: 28px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}

.modal h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-primary);
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 24px;
}

.modal-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.required {
  color: #ff3b30;
}

.modal-form input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-form input:focus {
  border-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-cancel {
  padding: 8px 18px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
}

.btn-confirm {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.btn-confirm:hover {
  background: var(--accent-hover);
}
</style>
