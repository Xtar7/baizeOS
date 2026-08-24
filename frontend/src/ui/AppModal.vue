<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Icon from '@/ui/Icon.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    width?: number
    /** 点击遮罩不关闭（表单填写中） */
    persistent?: boolean
    busy?: boolean
  }>(),
  { width: 460, persistent: false, busy: false },
)

const emit = defineEmits<{ (e: 'update:open', v: boolean): void }>()

const panelRef = ref<HTMLElement | null>(null)
let lastFocused: Element | null = null

function close() {
  if (props.busy) return
  emit('update:open', false)
}

function onOverlayClick() {
  if (!props.persistent) close()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.stopPropagation()
    close()
    return
  }
  // 简易焦点圈：Tab 循环在面板内
  if (e.key === 'Tab' && panelRef.value) {
    const focusables = panelRef.value.querySelectorAll<HTMLElement>(
      'button, input, textarea, select, [tabindex]:not([tabindex="-1"])',
    )
    if (!focusables.length) return
    const first = focusables[0]!
    const last = focusables[focusables.length - 1]!
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      lastFocused = document.activeElement
      document.body.style.overflow = 'hidden'
      await nextTick()
      const target = panelRef.value?.querySelector<HTMLElement>(
        'input, textarea, select, button',
      )
      target?.focus()
    } else {
      document.body.style.overflow = ''
      if (lastFocused instanceof HTMLElement) lastFocused.focus()
    }
  },
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="modal-overlay" @mousedown.self="onOverlayClick" @keydown="onKeydown">
        <Transition name="pop" appear>
          <div
            ref="panelRef"
            class="modal-panel"
            role="dialog"
            aria-modal="true"
            :aria-label="title"
            :style="{ maxWidth: `${width}px` }"
          >
            <header class="modal-head">
              <h2 class="modal-title">{{ title }}</h2>
              <button class="modal-close" type="button" aria-label="关闭" :disabled="busy" @click="close">
                <Icon name="x" :size="17" />
              </button>
            </header>
            <div class="modal-body">
              <slot />
            </div>
            <footer v-if="$slots.footer" class="modal-foot">
              <slot name="footer" />
            </footer>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: var(--overlay);
  display: grid;
  place-items: center;
  padding: 20px;
}

.modal-panel {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-modal);
  display: flex;
  flex-direction: column;
  max-height: min(86dvh, 720px);
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 0;
}

.modal-title {
  font-size: 16.5px;
  font-weight: 600;
}

.modal-close {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--ink-3);
  transition: background-color 0.15s ease-out;
}

.modal-close:hover:not(:disabled) {
  background: var(--surface-well);
  color: var(--ink);
}

.modal-body {
  padding: 14px 20px 6px;
  overflow-y: auto;
}

.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px 18px;
}
</style>
