<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'solid' | 'soft' | 'ghost' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    type?: 'button' | 'submit'
    disabled?: boolean
    loading?: boolean
    block?: boolean
  }>(),
  { variant: 'soft', size: 'md', type: 'button' },
)
</script>

<template>
  <button
    :type="type"
    class="btn"
    :class="[`btn--${variant}`, `btn--${size}`, { 'btn--block': block }]"
    :disabled="disabled || loading"
  >
    <svg v-if="loading" class="btn__spin" viewBox="0 0 20 20" width="15" height="15" aria-hidden="true">
      <circle cx="10" cy="10" r="7.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="33" stroke-dashoffset="26" />
    </svg>
    <span v-if="$slots.icon && !loading" class="btn__icon"><slot name="icon" /></span>
    <span class="btn__label"><slot /></span>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-weight: 500;
  border-radius: 10px;
  border: 1px solid transparent;
  white-space: nowrap;
  transition:
    background-color 0.15s ease-out,
    border-color 0.15s ease-out,
    color 0.15s ease-out,
    transform 0.12s ease-out;
  user-select: none;
}

.btn:active:not(:disabled) {
  transform: scale(0.98);
}

.btn:disabled {
  opacity: 0.55;
}

.btn--sm {
  height: 30px;
  padding: 0 11px;
  font-size: 13px;
}

.btn--md {
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
}

.btn--lg {
  height: 42px;
  padding: 0 20px;
  font-size: 14.5px;
}

.btn--block {
  width: 100%;
}

/* 主操作：暖炭底（深色主题下反转为米白） */
.btn--solid {
  background: var(--btn-solid-bg);
  color: var(--btn-solid-fg);
}

.btn--solid:hover:not(:disabled) {
  background: var(--btn-solid-bg-hover);
}

/* 次要：表面 + 细线 */
.btn--soft {
  background: var(--surface);
  color: var(--ink);
  border-color: var(--line-strong);
  box-shadow: 0 1px 1.5px rgb(28 25 23 / 4%);
}

.btn--soft:hover:not(:disabled) {
  background: var(--surface-well);
  border-color: var(--ink-faint);
}

/* 幽灵 */
.btn--ghost {
  color: var(--ink-2);
}

.btn--ghost:hover:not(:disabled) {
  background: var(--accent-soft);
  color: var(--ink);
}

/* 危险 */
.btn--danger {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: transparent;
}

.btn--danger:hover:not(:disabled) {
  background: var(--danger);
  color: #fff;
}

.btn__spin {
  animation: btn-spin 0.8s linear infinite;
}

@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
}

.btn__icon {
  display: inline-flex;
}
</style>
