import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark'
export type ToastType = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
}

export interface ConfirmOptions {
  title: string
  body?: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

interface ConfirmState extends Required<Omit<ConfirmOptions, 'body'>> {
  open: boolean
  body: string
  resolve: ((ok: boolean) => void) | null
}

const THEME_KEY = 'baizeos.theme'

function systemDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export const useSettingsStore = defineStore('settings', () => {
  // ============ 主题 ============
  const theme = ref<ThemeMode>(
    localStorage.getItem(THEME_KEY) === 'dark' || localStorage.getItem(THEME_KEY) === 'light'
      ? (localStorage.getItem(THEME_KEY) as ThemeMode)
      : systemDark()
        ? 'dark'
        : 'light',
  )

  function applyTheme() {
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
    const meta = document.querySelector('meta[name="theme-color"]')
    meta?.setAttribute('content', theme.value === 'dark' ? '#262624' : '#FAF9F5')
  }

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  watch(theme, () => {
    localStorage.setItem(THEME_KEY, theme.value)
    applyTheme()
  })
  applyTheme()

  // ============ Toast 通知 ============
  const toasts = ref<Toast[]>([])
  let toastSeq = 0

  function toast(message: string, type: ToastType = 'info') {
    const id = ++toastSeq
    toasts.value.push({ id, type, message })
    if (toasts.value.length > 5) toasts.value.shift()
    window.setTimeout(() => dismissToast(id), type === 'error' ? 6000 : 4200)
  }

  function dismissToast(id: number) {
    const i = toasts.value.findIndex((t) => t.id === id)
    if (i !== -1) toasts.value.splice(i, 1)
  }

  // ============ 确认对话框（promise 化） ============
  const confirmState = ref<ConfirmState>({
    open: false,
    title: '',
    body: '',
    confirmText: '确认',
    cancelText: '取消',
    danger: false,
    resolve: null,
  })

  function confirm(options: ConfirmOptions): Promise<boolean> {
    return new Promise((resolve) => {
      // 若已有未决确认，先以取消收场
      confirmState.value.resolve?.(false)
      confirmState.value = {
        open: true,
        title: options.title,
        body: options.body ?? '',
        confirmText: options.confirmText ?? '确认',
        cancelText: options.cancelText ?? '取消',
        danger: options.danger ?? false,
        resolve,
      }
    })
  }

  function settleConfirm(ok: boolean) {
    confirmState.value.resolve?.(ok)
    confirmState.value.resolve = null
    confirmState.value.open = false
  }

  /** 后端可达性提示点 */
  const backendHint = ref('http://localhost:5000')

  const isDark = computed(() => theme.value === 'dark')

  return {
    theme,
    isDark,
    toggleTheme,
    toasts,
    toast,
    dismissToast,
    confirmState,
    confirm,
    settleConfirm,
    backendHint,
  }
})
