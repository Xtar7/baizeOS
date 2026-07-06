import axios from 'axios'
import { useSettingsStore } from '@/stores/settings'

const BASE_URL = import.meta.env.DEV ? '/v1' : '/v1'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => config, (error) => Promise.reject(error))

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const settingsStore = useSettingsStore()
    const message = error.response?.data?.detail || error.response?.data?.error || error.message
    settingsStore.showToast(`请求失败: ${message}`, 'error')
    return Promise.reject(error)
  }
)

export default api
