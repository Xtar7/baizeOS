<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useKbStore } from '@/stores/kb'
import { chatCompletions } from '@/api/chat'
import MarkdownIt from 'markdown-it'

const chatStore = useChatStore()
const kbStore = useKbStore()

const inputText = ref('')
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const messages = computed(() => chatStore.messages)

async function sendMessage(text?: string) {
  const content = (text || inputText.value).trim()
  if (!content) return

  chatStore.addMessage('user', content)
  if (!text) inputText.value = ''

  const assistantId = chatStore.addMessage('assistant', '')
  chatStore.updateMessage(assistantId, '思考中...')

  try {
    const history = chatStore.messages
      .filter((m: any) => m.role !== 'assistant' || m.id !== assistantId)
      .map((m: any) => ({ role: m.role, content: m.content }))

    const res = await chatCompletions(history, {
      kbId: chatStore.ragEnabled && chatStore.currentKbId ? chatStore.currentKbId : undefined,
      stream: false,
    })

    const reply = res.data.choices?.[0]?.message?.content || '抱歉，未能获取回复。'
    chatStore.updateMessage(assistantId, reply)
  } catch (e: unknown) {
    const err = e as { message?: string }
    chatStore.updateMessage(assistantId, `请求失败: ${err.message || '未知错误'}`)
  }
}
</script>

<template>
  <div class="chat-view">
    <!-- Empty state -->
    <div v-if="messages.length === 0" class="chat-empty">
      <div class="chat-empty-inner">
        <div class="chat-empty-icon">◆</div>
        <h1>你好，我是 baizeOS</h1>
        <p>我可以帮你回答问题、分析文档、编写代码</p>
        <div class="chat-suggestions">
          <button class="suggestion" @click="sendMessage('帮我写一个Python快速排序算法')">
            帮我写一个 Python 快速排序算法
          </button>
          <button class="suggestion" @click="sendMessage('解释一下什么是向量数据库')">
            解释一下什么是向量数据库
          </button>
          <button class="suggestion" @click="sendMessage('用通俗的语言介绍RAG技术')">
            用通俗的语言介绍 RAG 技术
          </button>
          <button class="suggestion" @click="sendMessage('分析这段代码的性能问题')">
            分析这段代码的性能问题
          </button>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div v-else class="chat-messages">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message"
        :class="msg.role"
      >
        <div class="message-avatar">
          {{ msg.role === 'user' ? '👤' : '◆' }}
        </div>
        <div class="message-content">
          <div class="message-text" v-html="md.render(msg.content)" />
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="chat-input-area">
      <div class="input-row">
        <div class="rag-controls">
          <button
            class="rag-toggle"
            :class="{ active: chatStore.ragEnabled && chatStore.currentKbId }"
            @click="chatStore.ragEnabled = !chatStore.ragEnabled"
            title="RAG 知识库问答"
          >
            RAG
          </button>
          <select
            v-if="chatStore.ragEnabled"
            v-model="chatStore.currentKbId"
            class="kb-select"
          >
            <option value="">— 选择知识库 —</option>
            <option v-for="kb in kbStore.list" :key="kb.kb_id" :value="kb.kb_id">
              {{ kb.display_name }}
            </option>
          </select>
        </div>
        <textarea
          v-model="inputText"
          class="chat-textarea"
          placeholder="输入消息... (Ctrl+Enter 发送)"
          rows="1"
          @keydown.ctrl.enter="sendMessage()"
          @keydown.enter.prevent="sendMessage()"
        />
        <button class="send-btn" @click="sendMessage()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

/* Empty state */
.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-empty-inner {
  text-align: center;
  padding: 40px;
}

.chat-empty-icon {
  font-size: 48px;
  color: var(--accent);
  margin-bottom: 20px;
}

.chat-empty-inner h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.chat-empty-inner p {
  color: var(--text-secondary);
  margin-bottom: 32px;
}

.chat-suggestions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  max-width: 600px;
  margin: 0 auto;
}

.suggestion {
  padding: 14px 18px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
}

.suggestion:hover {
  border-color: var(--accent);
  background: var(--accent-light);
  transform: translateY(-1px);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.message-content {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
}

.message.user .message-content {
  background: var(--accent);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}

.message-text :deep(p) {
  margin: 4px 0;
}

.message-text :deep(code) {
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.9em;
}

.message-text :deep(pre) {
  background: var(--bg-secondary);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

/* Input area */
.chat-input-area {
  padding-top: 16px;
  border-top: 1px solid var(--border);
  margin-top: 16px;
}

.input-row {
  display: flex;
  align-items: stretch;
  gap: 10px;
}

.rag-controls {
  display: flex;
  align-items: stretch;
  gap: 8px;
}

.rag-toggle {
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 42px;
}

.rag-toggle.active {
  background: var(--accent-light);
  border-color: var(--accent);
  color: var(--accent);
}

.kb-select {
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  height: 42px;
  min-width: 120px;
  outline: none;
  transition: border-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.kb-select:focus {
  border-color: var(--accent);
}

.chat-textarea {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  font-family: var(--font-sans);
  resize: none;
  outline: none;
  transition: border-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 42px;
  max-height: 150px;
  line-height: 1.5;
}

.chat-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.send-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 150ms cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.send-btn:hover {
  background: var(--accent-hover);
}
</style>
