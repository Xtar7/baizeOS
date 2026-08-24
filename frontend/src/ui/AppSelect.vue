<script lang="ts">
/** 下拉选项（供外部 import type 使用） */
export interface SelectOption {
  label: string
  value: string
  meta?: string
}
</script>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Icon from '@/ui/Icon.vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    options: SelectOption[]
    placeholder?: string
    disabled?: boolean
    size?: 'sm' | 'md'
    /** 触发器外观：chip（输入台内）/ field（表单字段） */
    look?: 'chip' | 'field'
  }>(),
  { placeholder: '请选择', size: 'md', look: 'field' },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'change', v: string): void
}>()

const open = ref(false)
const activeIndex = ref(-1)
const triggerRef = ref<HTMLElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const panelStyle = ref<Record<string, string>>({})

const selected = computed(() => props.options.find((o) => o.value === props.modelValue))

function updatePosition() {
  const el = triggerRef.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const below = window.innerHeight - r.bottom
  const estimated = Math.min(props.options.length * 40 + 12, 280)
  const openUp = below < estimated + 16 && r.top > estimated + 16

  panelStyle.value = {
    left: `${Math.min(r.left, window.innerWidth - Math.max(r.width, 220) - 12)}px`,
    top: openUp ? 'auto' : `${r.bottom + 6}px`,
    bottom: openUp ? `${window.innerHeight - r.top + 6}px` : 'auto',
    width: `${Math.max(r.width, 200)}px`,
  }
}

async function openPanel() {
  if (props.disabled || open.value) return
  open.value = true
  activeIndex.value = Math.max(
    0,
    props.options.findIndex((o) => o.value === props.modelValue),
  )
  await nextTick()
  updatePosition()
  scrollActiveIntoView()
}

function closePanel(refocus = true) {
  if (!open.value) return
  open.value = false
  if (refocus) triggerRef.value?.focus()
}

function toggle() {
  open.value ? closePanel() : void openPanel()
}

function choose(option: SelectOption) {
  emit('update:modelValue', option.value)
  emit('change', option.value)
  closePanel()
}

function scrollActiveIntoView() {
  void nextTick(() => {
    const node = panelRef.value?.querySelector('[data-active="true"]')
    node?.scrollIntoView({ block: 'nearest' })
  })
}

function onTriggerKeydown(e: KeyboardEvent) {
  if (props.disabled) return
  switch (e.key) {
    case 'Enter':
    case ' ':
    case 'ArrowDown':
      e.preventDefault()
      void openPanel()
      break
    default:
      break
  }
}

function onPanelKeydown(e: KeyboardEvent) {
  if (!open.value) return
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      activeIndex.value = Math.min(activeIndex.value + 1, props.options.length - 1)
      scrollActiveIntoView()
      break
    case 'ArrowUp':
      e.preventDefault()
      activeIndex.value = Math.max(activeIndex.value - 1, 0)
      scrollActiveIntoView()
      break
    case 'Home':
      e.preventDefault()
      activeIndex.value = 0
      scrollActiveIntoView()
      break
    case 'End':
      e.preventDefault()
      activeIndex.value = props.options.length - 1
      scrollActiveIntoView()
      break
    case 'Enter':
    case ' ': {
      e.preventDefault()
      const opt = props.options[activeIndex.value]
      if (opt) choose(opt)
      break
    }
    case 'Escape':
      e.preventDefault()
      e.stopPropagation()
      closePanel()
      break
    case 'Tab':
      closePanel(false)
      break
    default:
      break
  }
}

function onDocPointerdown(e: PointerEvent) {
  if (!open.value) return
  const t = e.target as Node
  if (panelRef.value?.contains(t) || triggerRef.value?.contains(t)) return
  closePanel(false)
}

function onWindowResize() {
  if (open.value) closePanel(false)
}

document.addEventListener('pointerdown', onDocPointerdown, true)
window.addEventListener('resize', onWindowResize)
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocPointerdown, true)
  window.removeEventListener('resize', onWindowResize)
})

watch(
  () => props.options,
  () => {
    // 选项变化后当前值可能已不存在
    if (props.modelValue && !selected.value) emit('update:modelValue', '')
  },
)
</script>

<template>
  <div class="select" :class="`select--${size}`">
    <button
      ref="triggerRef"
      type="button"
      class="select__trigger"
      :class="[`select__trigger--${look}`, { 'is-open': open, 'is-placeholder': !selected }]"
      role="combobox"
      :aria-expanded="open"
      aria-haspopup="listbox"
      :disabled="disabled"
      @click="toggle"
      @keydown="onTriggerKeydown"
    >
      <span class="select__label">{{ selected?.label ?? placeholder }}</span>
      <Icon name="chevron-down" :size="14" class="select__caret" />
    </button>
  </div>

  <Teleport to="body">
    <Transition name="pop">
      <ul
        v-if="open"
        ref="panelRef"
        class="select-panel"
        :style="panelStyle"
        role="listbox"
        tabindex="-1"
        @keydown="onPanelKeydown"
      >
        <li
          v-for="(opt, i) in options"
          :key="opt.value"
          class="select-option"
          :data-active="i === activeIndex"
          :aria-selected="opt.value === modelValue"
          role="option"
          @mouseenter="activeIndex = i"
          @mousedown.prevent
          @click="choose(opt)"
        >
          <span class="select-option__check">
            <Icon v-if="opt.value === modelValue" name="check" :size="13" />
          </span>
          <span class="select-option__body">
            <span class="select-option__label">{{ opt.label }}</span>
            <span v-if="opt.meta" class="select-option__meta">{{ opt.meta }}</span>
          </span>
        </li>
        <li v-if="!options.length" class="select-empty">暂无可选项</li>
      </ul>
    </Transition>
  </Teleport>
</template>

<style scoped>
.select {
  display: inline-block;
  min-width: 0;
}

.select__trigger {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  text-align: left;
  border-radius: 10px;
  transition:
    background-color 0.15s ease-out,
    border-color 0.15s ease-out,
    color 0.15s ease-out;
}

.select--sm .select__trigger {
  height: 30px;
  font-size: 13px;
}

.select--md .select__trigger {
  height: 36px;
  font-size: 14px;
}

/* 表单字段形态 */
.select__trigger--field {
  background: var(--surface);
  border: 1px solid var(--line-strong);
  padding: 0 11px;
  color: var(--ink);
}

.select__trigger--field:hover:not(:disabled),
.select__trigger--field.is-open {
  border-color: var(--accent);
}

.select__trigger--field.is-placeholder {
  color: var(--ink-faint);
}

/* 输入台 chip 形态 */
.select__trigger--chip {
  background: var(--accent-soft);
  border: 1px solid transparent;
  padding: 0 10px;
  color: var(--ink-2);
  max-width: 240px;
}

.select__trigger--chip:hover:not(:disabled),
.select__trigger--chip.is-open {
  border-color: var(--accent-tint-line);
  color: var(--ink);
}

.select__trigger--chip .select__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select__label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select__caret {
  flex-shrink: 0;
  color: var(--ink-faint);
  transition: transform 0.15s ease-out;
}

.is-open .select__caret {
  transform: rotate(180deg);
}
</style>

<style>
/* teleport 面板（非 scoped） */
.select-panel {
  position: fixed;
  z-index: 110;
  margin: 0;
  padding: 5px;
  list-style: none;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-pop);
  max-height: 280px;
  overflow-y: auto;
  outline: none;
}

.select-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 9px;
  border-radius: 8px;
  cursor: pointer;
}

.select-option[data-active='true'] {
  background: var(--surface-well);
}

.select-option__check {
  width: 15px;
  flex-shrink: 0;
  color: var(--accent-text);
  display: inline-grid;
  place-items: center;
}

.select-option__body {
  min-width: 0;
}

.select-option__label {
  display: block;
  font-size: 13.5px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select-option__meta {
  display: block;
  font-size: 12px;
  color: var(--ink-3);
}

.select-empty {
  padding: 14px 10px;
  text-align: center;
  font-size: 13px;
  color: var(--ink-3);
}
</style>
