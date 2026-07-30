import api from './request'

export interface TmpFile {
  tmp_file_id: string
  object: string
  chat_id: string
  filename: string
  bytes: number
  created_at: number
  path: string
  mime_type: string
}

export async function uploadTmpFile(chatId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('chat_id', chatId)
  return api.post<{ message: string; file: TmpFile }>('files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function listTmpFiles(chatId: string) {
  return api.post<{ object: string; chat_id: string; total: number; data: TmpFile[] }>(
    'files/list',
    { chat_id: chatId }
  )
}

export async function deleteTmpFiles(
  chatId: string,
  fileIds: string[]
) {
  const payload = fileIds.length === 1
    ? { chat_id: chatId, tmp_file_id: fileIds[0] }
    : { chat_id: chatId, tmp_file_ids: fileIds }
  return api.post<{ chat_id: string; deleted_count: number; message: string }>(
    'files/delete',
    payload
  )
}
