import api from './request'
import type {
  Conversation,
  ConversationListResponse,
  CreateConversationPayload,
} from '@/types/api'

/** 列出会话（按 updated_at DESC） */
export function listConversations(userId = 'local') {
  return api
    .get<ConversationListResponse, ConversationListResponse>(
      `/conversations?user_id=${encodeURIComponent(userId)}`,
    )
    .then((r) => r.data ?? [])
}

/** 新建会话（前端可传入 conversation_id 做幂等） */
export function createConversation(payload: CreateConversationPayload = {}) {
  return api
    .post<Conversation, Conversation>('/conversations', payload)
    .then((r) => r)
}

/** 读取单条会话；includeMessages=true 时同时返回 messages */
export function getConversation(id: string, includeMessages = true) {
  return api
    .get<Conversation, Conversation>(
      `/conversations/${encodeURIComponent(id)}?include_messages=${includeMessages}`,
    )
    .then((r) => r)
}

/** 重命名会话 */
export function renameConversation(id: string, title: string) {
  return api
    .patch<Conversation, Conversation>(`/conversations/${encodeURIComponent(id)}`, {
      title,
    })
    .then((r) => r)
}

/** 软删会话 */
export function deleteConversation(id: string) {
  return api
    .delete<{ deleted: boolean; id: string }, { deleted: boolean; id: string }>(
      `/conversations/${encodeURIComponent(id)}`,
    )
    .then((r) => r)
}
