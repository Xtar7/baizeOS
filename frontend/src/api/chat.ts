import api from './request'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatCompletionResponse {
  id: string
  object: string
  created: number
  model: string
  choices: Array<{
    index: number
    message: ChatMessage
    finish_reason: string
  }>
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  references?: Array<{
    kb_id: string
    file_id: string
    chunk_id: string
    score: number
    content_preview: string
  }>
  safety?: {
    kb_hit: boolean
    hallucination_risk: string
    confidence: number
  }
}

export interface ChatChunk {
  id: string
  object: string
  choices: Array<{
    delta: { content?: string; role?: string }
    index: number
  }>
}

export async function chatCompletions(
  messages: ChatMessage[],
  options: { kbId?: string; stream?: boolean; model?: string } = {}
) {
  const { kbId, stream = false, model = 'default' } = options
  const payload: Record<string, unknown> = { model, messages, stream }
  if (kbId) {
    payload.rag = true
    payload.kb_id = kbId
  }
  return api.post<ChatCompletionResponse>('/chat/completions', payload)
}
