import axios, { type AxiosRequestConfig } from 'axios'

/**
 * 统一 Axios 实例。
 * 开发环境经 Vite 代理转发 /v1 → http://localhost:5000，无需关心跨域。
 */
const api = axios.create({
  baseURL: '/v1',
  timeout: 60_000, // RAG 操作可能较慢
})

/** 归一化后的业务错误：调用方 catch 后可直接 toast message */
export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status: number = error.response?.status ?? 0
    const data = error.response?.data as Record<string, unknown> | undefined
    // detail 是给人看的完整原因，error 是给机器看的短码（如 llm_unavailable）；
    // 两者并存时优先展示 detail。
    let message =
      (data?.detail as string) ??
      (data?.message as string) ??
      (data?.error as string) ??
      ''

    if (!message) {
      if (error.code === 'ECONNABORTED') message = '请求超时，请检查后端服务是否在运行'
      else if (status === 0) message = '无法连接后端服务（localhost:5000）'
      else if (status === 503) message = '后端暂时不可用（503），请稍后重试'
      else message = `请求失败（HTTP ${status}）`
    }

    return Promise.reject(new ApiError(message, status))
  },
)

/*
 * ── 以下四个 helper 是所有 API 函数的唯一出口 ──
 *
 * 为什么不直接用 `api.get<T, T>('/x')`：axios 的第二个泛型只影响**类型**，
 * 运行时返回的仍然是 AxiosResponse 对象。于是 `const kb = await api.get<KnowledgeBase,
 * KnowledgeBase>(...)` 在 TS 里被当成 KnowledgeBase，实际拿到的是
 * `{data, status, headers, config, request}` —— 访问 `kb.kb_id` 得到 undefined，
 * 且不会报任何类型错误。这正是"后端正常、前端全空"的根因。
 *
 * 这里统一剥掉一层，让 `apiGet<T>()` 的返回值就等于后端响应体，
 * 与所有调用点的写法（res.data / res.models / res.kb …）一致。
 */
export function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return api.get(url, config).then((r) => r.data as T)
}

export function apiPost<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return api.post(url, data, config).then((r) => r.data as T)
}

export function apiPut<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return api.put(url, data, config).then((r) => r.data as T)
}

export function apiPatch<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return api.patch(url, data, config).then((r) => r.data as T)
}

export function apiDelete<T>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> {
  return api.delete(url, config).then((r) => r.data as T)
}

export default api
