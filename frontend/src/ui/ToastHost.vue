<script setup lang="ts">
import { useSettingsStore } from '@/stores/settings'
import Icon from '@/ui/Icon.vue'

const store = useSettingsStore()

const ICON_BY_TYPE: Record<string, string> = {
  success: 'check',
  error: 'alert',
  info: 'spark',
}
</script>

<template>
  <div class="toast-region" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="t in store.toasts"
        :key="t.id"
        class="toast"
        :class="`toast--${t.type}`"
        role="status"
        @click="store.dismissToast(t.id)"
      >
        <span class="toast__icon"><Icon :name="ICON_BY_TYPE[t.type] ?? 'spark'" :size="15" /></span>
        <p class="toast__msg">{{ t.message }}</p>
        <button class="toast__close" type="button" aria-label="关闭提示" @click.stop="store.dismissToast(t.id)">
          <Icon name="x" :size="13" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-region {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 120;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: min(360px, calc(100vw - 32px));
  pointer-events: none;
}

.toast {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 11px 12px;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-pop);
  cursor: pointer;
}

.toast__icon {
  display: grid;
  place-items: center;
  margin-top: 1px;
}

.toast--success .toast__icon {
  color: var(--ok);
}

.toast--error .toast__icon {
  color: var(--danger);
}

.toast--info .toast__icon {
  color: var(--accent-text);
}

.toast__msg {
  flex: 1;
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--ink);
  overflow-wrap: anywhere;
}

.toast__close {
  color: var(--ink-faint);
  padding: 2px;
  border-radius: 5px;
  flex-shrink: 0;
}

.toast__close:hover {
  color: var(--ink);
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.2s ease-out,
    transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(14px);
}
</style>
