import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { StreamHandle } from '@/api/chat'
import { chatCompletionsStream } from '@/api/chat'
import * as fileApi from '@/api/file'
import * as convApi from '@/api/conversations'
import type {
  ChatMessageParam,
  ChatReference,
  ChatSafety,
  ChatUsage,
  Conversation,
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

/** 旧 key：仅作为"未连上后端时的离线草稿"读，不再主动写。 */
const LEGACY_DRAFT_KEY = 'baizeos.conversation'

function uid(): string {
  // 32 hex 字符（与后端 uuid.uuid4().hex 对齐），便于直接当 conversation_id
  if (typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  // fallback: 拼 32 hex
  let s = ''
  while (s.length < 32) s += Math.random().toString(16).slice(2)
  return s.slice(0, 32)
}

interface LegacyDraft {
  chatId: string
  ragEnabled: boolean
  kbId: string
  messages: ChatMsg[]
}

export const useChatStore = defineStore('chat', () => {
  const chatId = ref<string>(uid())
  const messages = ref<ChatMsg[]>([])
  const ragEnabled = ref(false)
  const selectedKbId = ref<string>('')
  const streaming = ref(false)

  // 当前会话的临时附件（服务端按 chat_id 归档）
  const tmpFiles = ref<TmpFile[]>([])
  const tmpLoading = ref(false)

  // ============ 多对话（后端持久化） ============
  const conversations = ref<Conversation[]>([])
  const conversationsLoading = ref(false)

  let handle: StreamHandle | null = null

  // ---------- 离线降级：只读旧 localStorage，新代码不写 ----------
  function restoreLegacyDraft() {
    try {
      const raw = localStorage.getItem(LEGACY_DRAFT_KEY)
      if (!raw) return
      const shape = JSON.parse(raw) as LegacyDraft
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
  restoreLegacyDraft()

  // 流式期间每个 delta 都会变更 messages，防抖后只写一条标记；不写消息内容
  let persistTimer = 0
  watch(
    [messages, chatId, ragEnabled, selectedKbId],
    () => {
      window.clearTimeout(persistTimer)
      persistTimer = window.setTimeout(() => {
        // 新方案下不再写 localStorage；保留 watch 只是为了让 onChange 副作用链不断
      }, 300)
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

  // ============ 多会话管理 ============
  async function loadConversations() {
    conversationsLoading.value = true
    try {
      conversations.value = await convApi.listConversations('local')
    } catch (e) {
      // 后端没起就当离线：列表空，不阻塞 UI
      conversations.value = []
      console.warn('[chat] loadConversations failed（离线？）', e)
    } finally {
      conversationsLoading.value = false
    }
  }

  /** 在后端建一条；离线/失败时仍返回新 id，本地先开新会话 */
  async function createConversation(): Promise<string> {
    const newId = uid()
    try {
      const conv = await convApi.createConversation({ conversation_id: newId })
      // 把新条目插到列表头
      const list = conversations.value
      const idx = list.findIndex((c) => c.id === conv.id)
      const item: Conversation = {
        id: conv.id,
        user_id: conv.user_id,
        title: conv.title,
        kb_id: conv.kb_id,
        message_count: conv.message_count,
        created_at: conv.created_at,
        updated_at: conv.updated_at,
      }
      if (idx === -1) conversations.value = [item, ...list]
      else conversations.value[idx] = item
      return newId
    } catch (e) {
      console.warn('[chat] createConversation 失败（离线模式）', e)
      return newId
    }
  }

  async function switchConversation(id: string) {
    if (id === chatId.value) return
    stop()
    chatId.value = id
    messages.value = []
    try {
      const conv = await convApi.getConversation(id, true)
      messages.value = (conv.messages ?? []).map((m) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        attachments: m.attachments ?? undefined,
        references: m.references ?? undefined,
        usage: m.usage ?? undefined,
        safety: m.safety ?? undefined,
        streaming: false,
        error: m.status === 'error',
      }))
    } catch (e) {
      console.warn('[chat] switchConversation 拉消息失败', e)
    }
    void refreshTmpFiles()
  }

  async function deleteConversation(id: string) {
    try {
      await convApi.deleteConversation(id)
    } catch (e) {
      console.warn('[chat] deleteConversation 失败', e)
    }
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (chatId.value === id) {
      const next = conversations.value[0]
      if (next) await switchConversation(next.id)
      else await newChat()
    }
  }

  async function renameConversation(id: string, title: string) {
    try {
      await convApi.renameConversation(id, title)
    } catch (e) {
      console.warn('[chat] rename 失败', e)
    }
    const c = conversations.value.find((x) => x.id === id)
    if (c) c.title = title
  }

  // ============ 会话 ============
  async function newChat() {
    if (streaming.value) stop()
    // 后端建一条；离线时仅本地换 id
    const newId = await createConversation()
    chatId.value = newId
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
        conversationId: chatId.value,
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
          // 流结束后异步刷新列表（标题、message_count、updated_at）
          void loadConversations()
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
          void loadConversations()
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

    // 列表里没当前 id → 触发一次刷新（首条消息时让侧边栏立刻出现这条）
    if (!conversations.value.some((c) => c.id === chatId.value)) {
      void loadConversations()
    }
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
    // 多对话
    conversations,
    conversationsLoading,
    loadConversations,
    switchConversation,
    deleteConversation,
    renameConversation,
    // 文件
    refreshTmpFiles,
    addTmpFiles,
    removeTmpFile,
    clearTmpFiles,
    // 会话动作
    newChat,
    send,
    stop,
    regenerate,
  }
})
