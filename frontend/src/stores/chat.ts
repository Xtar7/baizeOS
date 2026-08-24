import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { StreamHandle } from '@/api/chat'
import { chatCompletionsStream } from '@/api/chat'
import * as fileApi from '@/api/file'
import type {
  ChatMessageParam,
  ChatReference,
  ChatSafety,
  ChatUsage,
  TmpFile,
} from '@/types/api'

export interface ChatMsg {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** 发送时随消息展示的附件名 */
  attachments?: string[]
  references?: ChatReference[]
  safety?: ChatSafety
  usage?: ChatUsage
  streaming?: boolean
  error?: boolean
}

const PERSIST_KEY = 'baizeos.conversation'

function uid(): string {
  return typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

interface PersistShape {
  chatId: string
  ragEnabled: boolean
  kbId: string
  messages: ChatMsg[]
}

export const useChatStore = defineStore('chat', () => {
  const chatId = ref(uid())
  const messages = ref<ChatMsg[]>([])
  const ragEnabled = ref(false)
  const selectedKbId = ref<string>('')
  const streaming = ref(false)

  // 当前会话的临时附件（服务端按 chat_id 归档）
  const tmpFiles = ref<TmpFile[]>([])
  const tmpLoading = ref(false)

  let handle: StreamHandle | null = null

  // ============ 持久化 ============
  function persist() {
    const shape: PersistShape = {
      chatId: chatId.value,
      ragEnabled: ragEnabled.value,
      kbId: selectedKbId.value,
      // 流式中的占位消息不落盘
      messages: messages.value.filter((m) => !m.streaming),
    }
    try {
      localStorage.setItem(PERSIST_KEY, JSON.stringify(shape))
    } catch {
      /* 存储满等异常忽略 */
    }
  }

  function restore() {
    try {
      const raw = localStorage.getItem(PERSIST_KEY)
      if (!raw) return
      const shape = JSON.parse(raw) as PersistShape
      if (shape.chatId) chatId.value = shape.chatId
      ragEnabled.value = Boolean(shape.ragEnabled)
      selectedKbId.value = shape.kbId ?? ''
      messages.value = Array.isArray(shape.messages)
        ? shape.messages.map((m) => ({ ...m, streaming: false }))
        : []
    } catch {
      /* 损坏的存档直接丢弃 */
    }
  }

  restore()

  // 流式期间每个 delta 都会变更 messages，防抖后落盘
  let persistTimer = 0
  watch(
    [messages, chatId, ragEnabled, selectedKbId],
    () => {
      window.clearTimeout(persistTimer)
      persistTimer = window.setTimeout(persist, 300)
    },
    { deep: true },
  )

  // ============ 临时附件 ============
  async function refreshTmpFiles() {
    tmpLoading.value = true
    try {
      const res = await fileApi.listTmpFiles(chatId.value)
      tmpFiles.value = res.data ?? []
    } catch {
      tmpFiles.value = []
    } finally {
      tmpLoading.value = false
    }
  }

  async function addTmpFiles(files: File[]): Promise<{ ok: number; failed: string[] }> {
    const failed: string[] = []
    let ok = 0
    for (const f of files) {
      try {
        await fileApi.uploadTmpFile(chatId.value, f)
        ok++
      } catch (err) {
        failed.push(f.name)
        console.error('附件上传失败', err)
      }
    }
    await refreshTmpFiles()
    return { ok, failed }
  }

  async function removeTmpFile(id: string) {
    await fileApi.deleteTmpFiles(chatId.value, id)
    await refreshTmpFiles()
  }

  async function clearTmpFiles() {
    if (!tmpFiles.value.length) return
    const ids = tmpFiles.value.map((f) => f.tmp_file_id)
    await fileApi.deleteTmpFiles(chatId.value, ids)
    await refreshTmpFiles()
  }

  // ============ 会话 ============
  function newChat() {
    stop()
    chatId.value = uid()
    messages.value = []
    tmpFiles.value = []
    void refreshTmpFiles()
  }

  function stop() {
    handle?.abort()
    handle = null
    streaming.value = false
    messages.value.forEach((m) => {
      if (m.streaming) m.streaming = false
    })
  }

  /** 组装 OpenAI 消息历史并流式补全（历史最后一条须为用户消息） */
  async function runCompletion() {
    const history: ChatMessageParam[] = messages.value
      .filter((m) => !m.streaming && !m.error && m.content.trim())
      .map((m) => ({ role: m.role, content: m.content }))
    if (!history.length || history[history.length - 1]!.role !== 'user') return

    const placeholder: ChatMsg = {
      id: uid(),
      role: 'assistant',
      content: '',
      streaming: true,
    }
    messages.value.push(placeholder)
    streaming.value = true

    handle = await chatCompletionsStream(
      history.slice(-24), // 控制上下文长度
      {
        model: 'default',
        rag: ragEnabled.value && !!selectedKbId.value,
        kbId: selectedKbId.value || undefined,
      },
      {
        onDelta(text) {
          placeholder.content += text
        },
        onDone(meta) {
          placeholder.streaming = false
          placeholder.references = meta.references?.length ? meta.references : undefined
          placeholder.safety = meta.safety
          placeholder.usage = meta.usage
          streaming.value = false
          handle = null
        },
        onError(message) {
          placeholder.streaming = false
          streaming.value = false
          handle = null
          if (!placeholder.content) {
            placeholder.error = true
            placeholder.content = message
          } else {
            placeholder.error = true
            placeholder.references = undefined
          }
        },
      },
    )
  }

  async function send(text: string, attachmentNames?: string[]) {
    const trimmed = text.trim()
    if (!trimmed || streaming.value) return

    messages.value.push({
      id: uid(),
      role: 'user',
      content: trimmed,
      attachments: attachmentNames?.length ? attachmentNames : undefined,
    })

    await runCompletion()
  }

  /** 重新生成：截掉最后一条助手消息后重发 */
  async function regenerate() {
    if (streaming.value) return
    const lastUserIdx = findLastIndex(messages.value, (m) => m.role === 'user')
    if (lastUserIdx === -1) return
    // 移除其后的所有助手消息
    messages.value.splice(lastUserIdx + 1)
    await runCompletion()
  }

  function findLastIndex<T>(arr: T[], pred: (item: T) => boolean): number {
    for (let i = arr.length - 1; i >= 0; i--) {
      if (pred(arr[i]!)) return i
    }
    return -1
  }

  return {
    chatId,
    messages,
    ragEnabled,
    selectedKbId,
    streaming,
    tmpFiles,
    tmpLoading,
    refreshTmpFiles,
    addTmpFiles,
    removeTmpFile,
    clearTmpFiles,
    newChat,
    send,
    stop,
    regenerate,
  }
})
