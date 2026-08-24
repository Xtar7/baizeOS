import type {
  CreateKbPayload,
  DeleteFilesResponse,
  DeleteKbResponse,
  KbListResponse,
  KnowledgeBase,
  ReindexResponse,
  UpdateKbPayload,
  UpdateKbResponse,
  UploadToKbResponse,
} from '@/types/api'
import api from './request'

/** 创建知识库 — POST /v1/kb */
export function createKB(payload: CreateKbPayload) {
  return api.post<KnowledgeBase, KnowledgeBase>('/kb', payload).then((r) => r)
}

/** 列出所有知识库 — GET /v1/kb/list */
export function listKB() {
  return api.get<KbListResponse, KbListResponse>('/kb/list')
}

/** 获取单个知识库详情（含 files 数组）— GET /v1/kb/{kb_id} */
export function getKB(kbId: string) {
  return api.get<KnowledgeBase, KnowledgeBase>(`/kb/${encodeURIComponent(kbId)}`)
}

/** 更新知识库信息 — PUT /v1/kb/{kb_id}；needs_rebuild=true 时前端应提示重建 */
export function updateKB(kbId: string, payload: UpdateKbPayload) {
  return api.put<UpdateKbResponse, UpdateKbResponse>(`/kb/${encodeURIComponent(kbId)}`, payload)
}

/**
 * 删除知识库（单条或批量）— DELETE /v1/kb
 * 注意：DELETE + JSON body，不是 path 参数。
 */
export function deleteKB(payload: { kb_id: string } | { kb_ids: string[] }) {
  return api.delete<DeleteKbResponse, DeleteKbResponse>('/kb', { data: payload })
}

/**
 * 上传文件到知识库 — POST /v1/kb/upload (multipart/form-data)
 * 关键：文件字段名必须是 "file"（单数），不是 "files"。支持 .txt / .md / .pdf。
 * 上传后后端自动解析 → 切分 → 向量化 → 入库，因此耗时较长，带进度回调。
 */
export function uploadToKB(kbId: string, file: File, onProgress?: (percent: number) => void) {
  const formData = new FormData()
  formData.append('file', file) // 字段名必须是 file
  formData.append('kb_id', kbId)
  return api.post<UploadToKbResponse, UploadToKbResponse>('/kb/upload', formData, {
    timeout: 300_000, // 大文件 + 向量化耗时
    onUploadProgress(e) {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
}

/**
 * 删除知识库内文件（单条或批量）— DELETE /v1/kb/files
 * 单条字段 kb_file_id，批量字段 kb_file_ids（复数）。
 */
export function deleteKBFiles(kbId: string, fileIds: string | string[]) {
  const ids = Array.isArray(fileIds) ? fileIds : [fileIds]
  const payload =
    ids.length === 1 ? { kb_file_id: ids[0] } : { kb_file_ids: ids }
  return api.delete<DeleteFilesResponse, DeleteFilesResponse>('/kb/files', {
    data: { kb_id: kbId, ...payload },
  })
}

/** 重建向量索引 — POST /v1/kb/{kb_id}/reindex；force=true 强制重建。耗时操作。 */
export function reindexKB(kbId: string, force = false) {
  return api.post<ReindexResponse, ReindexResponse>(
    `/kb/${encodeURIComponent(kbId)}/reindex`,
    { force },
    { timeout: 600_000 },
  )
}
