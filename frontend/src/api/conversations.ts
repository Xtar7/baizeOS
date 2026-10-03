import type {
  Conversation,
  ConversationListResponse,
  CreateConversationPayload,
} from '@/types/api'
import { apiDelete, apiGet, apiPatch, apiPost } from './request'

/*
 * 约定：本文件的每个函数都直接返回**响应体**（不是 AxiosResponse）。
 */

/** 列出会话（按 updated_at DESC），取其中的数组 */
export function listConversations(userId = 'local') {
  return apiGet<ConversationListResponse>(
    `/conversations?user_id=${encodeURIComponent(userId)}`,
  ).then((r) => r?.data ?? [])
}

/** 新建会话（前端可传入 conversation_id 做幂等） */
export function createConversation(payload: CreateConversationPayload = {}) {
  return apiPost<Conversation>('/conversations', payload)
}

/** 读取单条会话；includeMessages=true 时同时返回 messages */
export function getConversation(id: string, includeMessages = true) {
  return apiGet<Conversation>(
    `/conversations/${encodeURIComponent(id)}?include_messages=${includeMessages}`,
  )
}

/** 重命名会话 */
export function renameConversation(id: string, title: string) {
  return apiPatch<Conversation>(`/conversations/${encodeURIComponent(id)}`, { title })
}

/** 软删会话 */
export function deleteConversation(id: string) {
  return apiDelete<{ deleted: boolean; id: string }>(
    `/conversations/${encodeURIComponent(id)}`,
  )
}
