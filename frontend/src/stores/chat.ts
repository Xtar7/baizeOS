import { defineStore } from 'pinia'
import { reactive, ref, watch } from 'vue'
import type { StreamHandle } from '@/api/chat'
import { chatCompletionsStream } from '@/api/chat'
import { ApiError } from '@/api/request'
import * as fileApi from '@/api/file'
import * as convApi from '@/api/conversations'
import type {
  ChatMessageParam,
  ChatReference,
  ChatSafety,
  ChatUsage,
  Conversation,
  ConversationMessage,
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

/**
 * 旧版把整份对话（消息正文 + chat_id）冻在 localStorage 里，多对话上线后
 * 这份存档再没被更新过，却仍在每次启动时被原样恢复 —— 表现就是"新开了对话，
 * 一刷新又回到之前某次失败的页面"，而且永远删不掉。直接清掉。
 */
const LEGACY_DRAFT_KEY = 'baizeos.conversation'
/** 当前会话 id —— 只记 id 不记内容，刷新后据此回后端拉真实历史。 */
const ACTIVE_CONV_KEY = 'baizeos.activeConversationId'

/** 后端 id 形如 uuid4().hex（32 位小写 hex），用来挡掉手改坏的值 */
const CONV_ID_RE = /^[0-9a-f]{32}$/

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

function readActiveId(): string {
  try {
    const raw = localStorage.getItem(ACTIVE_CONV_KEY)
    return raw && CONV_ID_RE.test(raw) ? raw : ''
  } catch {
    return '' // 隐私模式等场景下 localStorage 可能直接抛
  }
}

function persistActiveId(id: string) {
  try {
    if (id) localStorage.setItem(ACTIVE_CONV_KEY, id)
    else localStorage.removeItem(ACTIVE_CONV_KEY)
  } catch {
    /* 写不进去只影响"刷新后回到哪条会话"，聊天本身不受影响 */
  }
}

/** 后端消息 → 界面消息 */
function toMsgs(list?: ConversationMessage[] | null): ChatMsg[] {
  return (list ?? []).map((m) => ({
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
}

export const useChatStore = defineStore('chat', () => {
  const chatId = ref<string>(readActiveId() || uid())
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

  // 清掉旧版离线草稿：留着只会让"回到某次失败的对话"这件事反复发生
  try {
    localStorage.removeItem(LEGACY_DRAFT_KEY)
  } catch {
    /* 同上，写不了就算了 */
  }

  // 首屏也写一次：新会话在发出第一条消息后就已经存在于后端，
  // 但 chatId 全程不变，只靠 watch 的话这次切换不会被记录下来。
  watch(chatId, persistActiveId)
  persistActiveId(chatId.value)

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
      if (chatId.value !== id) return // 拉取期间又切走了，丢弃这次结果
      messages.value = toMsgs(conv.messages)
    } catch (e) {
      console.warn('[chat] switchConversation 拉消息失败', e)
    }
    void refreshTmpFiles()
  }

  /**
   * 首屏引导：回到上次停留的那条对话；没有存档、或存档指向的对话已被删除，
   * 就停在一张干净的新对话页。
   *
   * 关键在于"取回"是一次**向后端核对**过的事，而不是无条件相信 localStorage ——
   * 无条件恢复存档正是"刷新后回到某次失败的老对话、且删不掉"的成因。
   */
  async function initConversation() {
    void loadConversations() // 侧边栏列表与恢复当前对话互不依赖，并行即可

    const saved = readActiveId()
    if (!saved) return // 首次访问：chatId 已经是刚生成的新 id，停在空白页

    try {
      const conv = await convApi.getConversation(saved, true)
      if (chatId.value !== saved) return // 引导期间用户已切换/新开，交给当前状态
      messages.value = toMsgs(conv.messages)
      void refreshTmpFiles()
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0
      if (status === 404) {
        // 对话已被删除：忘掉这个存档，重新开一页干净的
        chatId.value = uid()
        messages.value = []
      }
      // status 0 = 后端没起，其他错误同理：保留存档，下次刷新还能回到这里
      console.warn('[chat] initConversation 恢复上次对话失败', e)
    }
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

    // 必须是 reactive：messages 是 ref([])，push 进去的是响应式代理，
    // 而回调里闭包持有的是这个原始对象。裸对象上的 `content +=` 不会触发
    // 依赖收集，界面会永远停在"思考中"。包一层后 push 的是同一个代理，
    // 改它就等于改组件读的那个对象。
    const placeholder = reactive<ChatMsg>({
      id: uid(),
      role: 'assistant',
      content: '',
      streaming: true,
    })
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
    initConversation,
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
