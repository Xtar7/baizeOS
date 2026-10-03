import type { EmbeddingListResponse, LlmListResponse } from '@/types/api'
import { apiGet } from './request'

/** 列出本地 LLM 模型 — GET /v1/models */
export function listModels() {
  return apiGet<LlmListResponse>('/models')
}

/** 列出可用 Embedding 模型 — GET /v1/rag/embedding_models */
export function listEmbeddingModels() {
  return apiGet<EmbeddingListResponse>('/rag/embedding_models')
}
