import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  streaming?: boolean
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const currentKbId = ref<string>('')
  const ragEnabled = ref(false)
  const isStreaming = ref(false)
  let messageIdCounter = 0

  function generateId() {
    return `msg_${++messageIdCounter}_${Date.now()}`
  }

  function addMessage(role: 'user' | 'assistant', content: string) {
    const msg: Message = {
      id: generateId(),
      role,
      content,
      timestamp: Date.now(),
    }
    messages.value.push(msg)
    return msg.id
  }

  function updateMessage(id: string, content: string) {
    const msg = messages.value.find((m) => m.id === id)
    if (msg) {
      msg.content = content
      msg.streaming = false
    }
  }

  function clearMessages() {
    messages.value = []
    messageIdCounter = 0
  }

  return {
    messages,
    currentKbId,
    ragEnabled,
    isStreaming,
    addMessage,
    updateMessage,
    clearMessages,
  }
})
