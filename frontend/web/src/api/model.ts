import api from './request'

export interface LLMModel {
  id: string
  object: string
  created: number
  owned_by: string
}

export interface EmbeddingModel {
  name: string
  path: string
  dim: number
  type: string
  is_default: boolean
}

export async function listModels() {
  return api.get<{ object: string; data: LLMModel[] }>('/models')
}

export async function listEmbeddingModels() {
  return api.get<{
    models: EmbeddingModel[]
    default: string
    total: number
  }>('/rag/embedding_models')
}
