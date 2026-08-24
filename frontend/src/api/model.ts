import type { EmbeddingListResponse, LlmListResponse } from '@/types/api'
import api from './request'

/** 列出本地 LLM 模型 — GET /v1/models */
export function listModels() {
  return api.get<LlmListResponse, LlmListResponse>('/models')
}

/** 列出可用 Embedding 模型 — GET /v1/rag/embedding_models */
export function listEmbeddingModels() {
  return api.get<EmbeddingListResponse, EmbeddingListResponse>('/rag/embedding_models')
}
