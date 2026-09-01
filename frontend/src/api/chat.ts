import type {
  ChatMessageParam,
  ChatOptions,
  ChatUsage,
  StreamCallbacks,
} from '@/types/api'

export interface StreamHandle {
  abort: () => void
}

/**
 * RAG 对话（SSE 流式）— POST /v1/chat/completions, stream: true
 *
 * 后端事件流格式：
 *   data: {"choices":[{"delta":{"content":"…"}}]}
 *   data: {"done":true,"usage":{…},"references":[…],"safety":{…}}
 *   data: [DONE]
 *
 * 用 fetch + ReadableStream 解析（axios 在浏览器端无法增量读取流）。
 */
export async function chatCompletionsStream(
  messages: ChatMessageParam[],
  options: ChatOptions & { conversationId?: string } = {},
  callbacks: StreamCallbacks,
): Promise<StreamHandle> {
  const controller = new AbortController()
  const { model = 'default', rag = false, kbId, debug, conversationId } = options

  const payload: Record<string, unknown> = { model, messages, stream: true }
  if (rag && kbId) {
    payload.rag = true
    payload.kb_id = kbId
  }
  if (debug) payload.debug = true
  if (conversationId) payload.conversation_id = conversationId

  // 异步执行，调用方拿到 handle 即可 abort
  void (async () => {
    try {
      const response = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      })

      if (!response.ok) {
        let message = `请求失败（HTTP ${response.status}）`
        try {
          const data = (await response.json()) as Record<string, unknown>
          message = (data.error as string) ?? (data.detail as string) ?? message
        } catch {
          /* 非 JSON 错误体，保留默认信息 */
        }
        callbacks.onError(message)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        callbacks.onError('当前环境不支持流式读取')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let received = false

      const handleEvent = (raw: string) => {
        for (const line of raw.split('\n')) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (!data || data === '[DONE]') continue

          try {
            const chunk = JSON.parse(data) as Record<string, unknown>

            // 流中错误帧
            if (chunk.error) {
              callbacks.onError(String(chunk.detail ?? chunk.error))
              return
            }

            // 结束帧：携带 usage / references / safety
            if (chunk.done) {
              callbacks.onDone({
                usage: chunk.usage as ChatUsage | undefined,
                references: (chunk.references as never[]) ?? [],
                safety: chunk.safety as never | undefined,
              })
              continue
            }

            // 内容增量
            const choices = chunk.choices as { delta?: { content?: string } }[] | undefined
            const text = choices?.[0]?.delta?.content
            if (text) {
              received = true
              callbacks.onDelta(text)
            }
          } catch {
            /* 忽略非 JSON 行 */
          }
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // SSE 以空行分隔事件
        let sep: number
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const event = buffer.slice(0, sep)
          buffer = buffer.slice(sep + 2)
          handleEvent(event)
        }
      }

      // 处理残留缓冲
      if (buffer.trim()) handleEvent(buffer)

      if (!received) {
        // 流结束但没有任何内容增量，也没有 done 帧 —— 给用户一个明确信号
        callbacks.onError('模型未返回内容')
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        // 用户主动停止：正常收尾
        callbacks.onDone({})
        return
      }
      callbacks.onError(err instanceof Error ? err.message : '网络错误')
    }
  })()

  return { abort: () => controller.abort() }
}

/** 非流式对话 — POST /v1/chat/completions */
export async function chatCompletions(
  messages: ChatMessageParam[],
  options: ChatOptions & { conversationId?: string } = {},
) {
  const { model = 'default', rag = false, kbId, conversationId } = options
  const payload: Record<string, unknown> = { model, messages, stream: false }
  if (rag && kbId) {
    payload.rag = true
    payload.kb_id = kbId
  }
  if (conversationId) payload.conversation_id = conversationId
  const res = await fetch('/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`请求失败（HTTP ${res.status}）`)
  return (await res.json()) as Record<string, unknown>
}
