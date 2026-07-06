import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as kbApi from '@/api/kb'
import type { KBListItem, KBMeta } from '@/api/kb'

export const useKbStore = defineStore('kb', () => {
  const list = ref<KBListItem[]>([])
  const current = ref<KBMeta | null>(null)
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const res = await kbApi.listKB()
      list.value = res.data.data || []
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(kbId: string) {
    loading.value = true
    try {
      const res = await kbApi.getKB(kbId)
      current.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function create(data: {
    display_name: string
    system_prompt?: string
    description?: string
    embedding_model?: string
  }) {
    const res = await kbApi.createKB(data)
    return res.data
  }

  async function remove(kbId: string) {
    await kbApi.deleteKB({ kb_id: kbId })
    await fetchList()
  }

  return {
    list,
    current,
    loading,
    fetchList,
    fetchDetail,
    create,
    remove,
  }
})
