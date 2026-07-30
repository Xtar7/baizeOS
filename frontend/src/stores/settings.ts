import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useMessage } from 'naive-ui'

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<'light' | 'dark'>('light')
  const messages = ref<Array<{ id: string; text: string; type: 'success' | 'error' | 'info' | 'warning' }>>([])

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
  }

  function showToast(text: string, type: 'success' | 'error' | 'info' = 'info') {
    const msg = useMessage()
    msg[type](text, { duration: 3000 })
    return msg[type](text)
  }

  return { theme, messages, toggleTheme, showToast }
})
