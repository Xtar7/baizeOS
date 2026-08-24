<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMsg } from '@/stores/chat'
import { renderMarkdown } from '@/utils/markdown'
import Icon from '@/ui/Icon.vue'
import AppButton from '@/ui/AppButton.vue'
import ReferenceList from './ReferenceList.vue'

const props = defineProps<{ msg: ChatMsg; isLast: boolean }>()
const emit = defineEmits<{ (e: 'regenerate'): void }>()

const html = computed(() => renderMarkdown(props.msg.content))

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // 剪贴板 API 不可用时的兜底
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    ta.remove()
  }
}
</script>

<template>
  <!-- 用户消息：右对齐气泡 -->
  <div v-if="msg.role === 'user'" class="row row--user">
    <div class="bubble-user">
      <div v-if="msg.attachments?.length" class="bubble-user__files">
        <span v-for="name in msg.attachments ?? []" :key="name" class="file-chip">
          <Icon name="clip" :size="12" />
          {{ name }}
        </span>
      </div>
      <p class="bubble-user__text">{{ msg.content }}</p>
    </div>
  </div>

  <!-- 助手消息：全宽排版 -->
  <div v-else class="row row--ai">
    <span class="avatar" aria-hidden="true"><Icon name="spark" :size="14" :stroke-width="2" /></span>
    <div class="ai-body">
      <div
        v-if="msg.error"
        class="ai-error"
        role="alert"
      >
        <Icon name="alert" :size="16" />
        <p>{{ msg.content || '出错了，请稍后重试。' }}</p>
        <AppButton variant="soft" size="sm" @click="emit('regenerate')">重新生成</AppButton>
      </div>

      <template v-else>
        <div class="msg-prose ai-body__prose" :class="{ 'is-streaming': msg.streaming }" v-html="html" />
        <p v-if="msg.streaming && !msg.content" class="thinking">思考中<span class="dots" /></p>

        <ReferenceList v-if="!msg.streaming && msg.references?.length" :references="msg.references" />

        <p v-if="!msg.streaming && msg.safety && !msg.safety.kb_hit" class="safety-note">
          <Icon name="alert" :size="13" />
          本次回答未命中知识库内容，请谨慎甄别。
        </p>

        <div v-if="!msg.streaming && msg.content" class="msg-actions">
          <button class="msg-action" type="button" aria-label="复制回答" title="复制" @click="copyText(msg.content)">
            <Icon name="copy" :size="14" />
          </button>
          <button
            v-if="isLast"
            class="msg-action"
            type="button"
            aria-label="重新生成"
            title="重新生成"
            @click="emit('regenerate')"
          >
            <Icon name="refresh" :size="14" />
          </button>
          <span v-if="msg.usage?.total_tokens" class="token-count tabular">{{ msg.usage.total_tokens }} tokens</span>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.row {
  padding: 10px 0;
}

.row--user {
  display: flex;
  justify-content: flex-end;
}

.bubble-user {
  max-width: min(85%, 560px);
  background: var(--accent);
  color: var(--on-accent);
  border-radius: var(--r-lg);
  border-bottom-right-radius: 6px;
  padding: 10px 15px;
}

.bubble-user__files {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 7px;
}

.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  background: rgb(255 255 255 / 18%);
  border-radius: 6px;
  padding: 2px 8px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bubble-user__text {
  font-size: 15px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.row--ai {
  display: flex;
  gap: 13px;
}

.avatar {
  width: 27px;
  height: 27px;
  flex-shrink: 0;
  margin-top: 3px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: var(--surface-well);
  border: 1px solid var(--line);
  color: var(--accent-text);
}

.ai-body {
  flex: 1;
  min-width: 0;
}

.thinking {
  color: var(--ink-3);
  font-size: 14px;
}

.dots::after {
  content: '…';
  animation: dots-pulse 1.2s ease-in-out infinite alternate;
}

@keyframes dots-pulse {
  from {
    opacity: 0.3;
  }
  to {
    opacity: 1;
  }
}

@keyframes caret-blink {
  50% {
    opacity: 0;
  }
}

.ai-error {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 11px 14px;
  border: 1px solid var(--danger-line);
  background: var(--danger-soft);
  border-radius: var(--r-md);
  color: var(--danger);
  font-size: 14px;
}

.ai-error p {
  flex: 1;
}

.safety-note {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--warn);
  background: var(--warn-soft);
  border-radius: 7px;
  padding: 4px 9px;
}

.msg-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}

.msg-action {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  color: var(--ink-faint);
  transition:
    background-color 0.14s ease-out,
    color 0.14s ease-out;
}

.msg-action:hover {
  background: var(--surface-well);
  color: var(--ink);
}

.token-count {
  margin-left: 7px;
  font-size: 11.5px;
  color: var(--ink-faint);
}
</style>
