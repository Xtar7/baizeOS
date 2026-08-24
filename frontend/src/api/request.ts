import axios from 'axios'

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
    let message =
      (data?.error as string) ??
      (data?.detail as string) ??
      (data?.message as string) ??
      ''

    if (!message) {
      if (error.code === 'ECONNABORTED') message = '请求超时，请检查后端服务是否在运行'
      else if (status === 0) message = '无法连接后端服务（localhost:5000）'
      else message = `请求失败（HTTP ${status}）`
    }

    return Promise.reject(new ApiError(message, status))
  },
)

export default api
