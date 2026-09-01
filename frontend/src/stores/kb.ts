import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as kbApi from '@/api/kb'
import { listEmbeddingModels } from '@/api/model'
import type {
  CreateKbPayload,
  EmbeddingModel,
  KbListItem,
  KnowledgeBase,
  UpdateKbPayload,
} from '@/types/api'

export const useKbStore = defineStore('kb', () => {
  // ============ 列表 ============
  const list = ref<KbListItem[]>([])
  const loadingList = ref<boolean>(false)
  let listLoaded = false

  async function fetchList(force = false) {
    if (loadingList.value) return
    if (listLoaded && !force) return
    loadingList.value = true
    try {
      const res = await kbApi.listKB()
      list.value = res.data ?? []
      listLoaded = true
    } finally {
      loadingList.value = false
    }
    // 顺手把 embedding 模型也拉了，让"新建知识库"弹窗打开时立刻有选项
    void fetchEmbeddingModels().catch(() => undefined)
  }

  function invalidate() {
    listLoaded = false
  }

  /** 从列表缓存取展示名（引用卡片等场景） */
  function nameOf(kbId: string): string {
    return list.value.find((k) => k.kb_id === kbId)?.display_name ?? ''
  }

  // ============ 详情 ============
  const detail = ref<KnowledgeBase | null>(null)
  const loadingDetail = ref<boolean>(false)

  async function fetchDetail(kbId: string) {
    loadingDetail.value = true
    try {
      detail.value = await kbApi.getKB(kbId)
    } finally {
      loadingDetail.value = false
    }
  }

  function clearDetail() {
    detail.value = null
  }

  // ============ Embedding 模型目录 ============
  const embeddingModels = ref<EmbeddingModel[]>([])
  const defaultEmbedding = ref('')
  const modelsLoading = ref<boolean>(false)

  async function fetchEmbeddingModels(force = false) {
    if (modelsLoading.value) return
    if (embeddingModels.value.length && !force) return
    modelsLoading.value = true
    try {
      const res = await listEmbeddingModels()
      embeddingModels.value = res.models ?? []
      defaultEmbedding.value = res.default ?? ''
    } finally {
      modelsLoading.value = false
    }
  }

  // ============ CRUD ============
  async function create(payload: CreateKbPayload): Promise<KnowledgeBase> {
    const kb = await kbApi.createKB(payload)
    invalidate()
    return kb
  }

  async function update(kbId: string, payload: UpdateKbPayload) {
    const res = await kbApi.updateKB(kbId, payload)
    invalidate()
    return res
  }

  async function remove(kbIds: string | string[]) {
    const ids = Array.isArray(kbIds) ? kbIds : [kbIds]
    const payload = ids.length === 1 ? { kb_id: ids[0]! } : { kb_ids: ids }
    const res = await kbApi.deleteKB(payload)
    invalidate()
    return res
  }

  async function reindex(kbId: string, force = false) {
    return kbApi.reindexKB(kbId, force)
  }

  return {
    list,
    loadingList,
    fetchList,
    invalidate,
    nameOf,
    detail,
    loadingDetail,
    fetchDetail,
    clearDetail,
    embeddingModels,
    defaultEmbedding,
    modelsLoading,
    fetchEmbeddingModels,
    create,
    update,
    remove,
    reindex,
  }
})
