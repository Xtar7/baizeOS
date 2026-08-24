/** 后端接口类型定义 —— 与 docs/API调用方案.md、docs/接口规范.md 一一对应 */

// ============ 知识库 ============

export interface KbFile {
  kb_file_id: string
  filename: string
  path: string
  bytes: number
  created_at: string
  mime_type?: string
}

export interface KnowledgeBase {
  kb_id: string
  display_name: string
  description?: string
  system_prompt?: string
  embedding_model?: string
  embedding_dim?: number | null
  last_embedding_model?: string | null
  last_embedding_dim?: number | null
  created_at: string
  updated_at: string
  file_count?: number
  files?: KbFile[]
}

export interface KbListItem {
  kb_id: string
  display_name: string
  description?: string
  created_at: string
  updated_at: string
  file_count: number
}

export interface KbListResponse {
  object: 'list'
  data: KbListItem[]
  total: number
}

export interface CreateKbPayload {
  display_name: string
  system_prompt?: string
  description?: string
  embedding_model?: string
}

export interface UpdateKbPayload {
  display_name?: string
  system_prompt?: string
  description?: string
  embedding_model?: string
}

export interface UpdateKbResponse {
  kb: KnowledgeBase
  updated: boolean
  needs_rebuild: boolean
  rebuild_reason?: string
  message?: string
}

export interface DeleteKbResponse {
  deleted_count: number
  kb_ids: string[]
  failed?: { kb_id: string; reason: string }[]
  deleted?: boolean
}

export interface UploadToKbResponse {
  message: string
  kb_id: string
  file_info: KbFile
}

export interface DeleteFilesResponse {
  kb_id: string
  deleted_count?: number
  kb_file_id?: string
  kb_file_ids?: string[]
  deleted?: boolean
}

export interface ReindexResponse {
  status: 'completed' | 'skipped'
  message: string
  ingested_files: number
  total_files?: number
  chunks: number
  model_used?: string
  dim?: number
}

// ============ 模型 ============

export interface LlmModel {
  id: string
  object: 'model'
  created: number
  owned_by: string
}

export interface LlmListResponse {
  object: 'list'
  data: LlmModel[]
}

export interface EmbeddingModel {
  name: string
  path: string
  dim: number
  type: string
  is_default?: boolean
}

export interface EmbeddingListResponse {
  models: EmbeddingModel[]
  default: string
  total: number
}

// ============ 临时文件（聊天附件） ============

export interface TmpFile {
  tmp_file_id: string
  object: 'file'
  chat_id: string
  filename: string
  bytes: number
  created_at: number
  path: string
  mime_type: string
}

export interface TmpListResponse {
  object: 'list'
  chat_id: string
  total: number
  data: TmpFile[]
}

export interface TmpDeleteResponse {
  chat_id: string
  deleted_count: number
  message?: string
}

// ============ 对话 ============

export type ChatRole = 'system' | 'user' | 'assistant'

export interface ChatMessageParam {
  role: ChatRole
  content: string
}

export interface ChatUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface ChatReference {
  kb_id: string
  file_id: string
  chunk_id: string
  score: number
  content_preview: string
}

export interface ChatSafety {
  kb_hit: boolean
  hallucination_risk: 'low' | 'high' | string
  confidence: number
}

export interface ChatOptions {
  model?: string
  rag?: boolean
  kbId?: string
  debug?: boolean
}

export interface StreamCallbacks {
  onDelta: (text: string) => void
  onDone: (meta: { usage?: ChatUsage; references?: ChatReference[]; safety?: ChatSafety }) => void
  onError: (message: string) => void
}
