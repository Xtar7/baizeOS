import type { TmpDeleteResponse, TmpFile, TmpListResponse } from '@/types/api'
import api from './request'

/**
 * 上传临时文件（聊天附件）— POST /v1/files/upload (multipart/form-data)
 * 字段名必须是 "file"；必须携带 chat_id。
 */
export function uploadTmpFile(chatId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file) // 字段名必须是 file
  formData.append('chat_id', chatId)
  return api.post<{ message: string; file: TmpFile }, { message: string; file: TmpFile }>(
    '/files/upload',
    formData,
    { timeout: 180_000 },
  )
}

/** 列出某聊天的临时文件 — POST /v1/files/list（注意是 POST 不是 GET） */
export function listTmpFiles(chatId: string) {
  return api.post<TmpListResponse, TmpListResponse>('/files/list', { chat_id: chatId })
}

/**
 * 删除临时文件（单条或批量）— POST /v1/files/delete（注意是 POST 不是 DELETE）
 * 单条字段 tmp_file_id，批量字段 tmp_file_ids（复数）。
 */
export function deleteTmpFiles(chatId: string, fileIds: string | string[]) {
  const ids = Array.isArray(fileIds) ? fileIds : [fileIds]
  const payload =
    ids.length === 1 ? { tmp_file_id: ids[0] } : { tmp_file_ids: ids }
  return api.post<TmpDeleteResponse, TmpDeleteResponse>('/files/delete', {
    chat_id: chatId,
    ...payload,
  })
}
