import api from './request'

export interface KBFile {
  kb_file_id: string
  filename: string
  path: string
  bytes: number
  created_at: string
  mime_type: string
}

export interface KBMeta {
  kb_id: string
  display_name: string
  description: string
  system_prompt: string
  created_at: string
  updated_at: string
  embedding_model: string
  embedding_dim: number
  last_embedding_model: string | null
  last_embedding_dim: number | null
  files?: KBFile[]
}

export interface KBListItem {
  kb_id: string
  display_name: string
  description: string
  created_at: string
  updated_at: string
  file_count: number
}

export async function createKB(payload: {
  display_name: string
  system_prompt?: string
  description?: string
  embedding_model?: string
}) {
  return api.post<KBMeta>('/kb', payload)
}

export async function listKB() {
  return api.get<{ data: KBListItem[]; total: number }>('/kb/list')
}

export async function getKB(kbId: string) {
  return api.get<KBMeta>(`/kb/${kbId}`)
}

export async function updateKB(kbId: string, payload: Record<string, unknown>) {
  return api.put<{ kb: KBMeta; updated: boolean; needs_rebuild?: boolean }>(`/kb/${kbId}`, payload)
}

export async function deleteKB(payload: { kb_id: string } | { kb_ids: string[] }) {
  return api.delete<{ deleted_count: number; deleted: boolean }>('kb', { data: payload })
}

export async function uploadToKB(kbId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('kb_id', kbId)
  return api.post<{ message: string; file_info: KBFile }>('kb/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export async function deleteFiles(kbId: string, fileIds: string[]) {
  const payload = fileIds.length === 1
    ? { kb_id: kbId, kb_file_id: fileIds[0] }
    : { kb_id: kbId, kb_file_ids: fileIds }
  return api.delete<{ deleted_count: number }>('kb/files', { data: payload })
}

export async function reindexKB(kbId: string, force = false) {
  return api.post<{ status: string; ingested_files: number; chunks: number }>(
    `/kb/${kbId}/reindex`,
    { force }
  )
}
