<script setup lang="ts">
/** 内联 SVG 图标系统：统一 24 网格、1.6 描边、圆角端点，继承 currentColor */
import { computed } from 'vue'

const ICONS: Record<string, string> = {
  chat:
    '<path d="M12 4.25c4.83 0 8.75 3.22 8.75 7.25s-3.92 7.25-8.75 7.25c-.86 0-1.7-.1-2.48-.3L5.2 19.9l1.02-3.05C4.28 15.6 3.25 13.65 3.25 11.5c0-4.03 3.92-7.25 8.75-7.25Z"/><path d="M8.5 10.5h.01M12 10.5h.01M15.5 10.5h.01" stroke-width="2.4"/>',
  library:
    '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.75"/><path d="M4.5 5.5v6c0 1.52 3.36 2.75 7.5 2.75s7.5-1.23 7.5-2.75v-6"/><path d="M4.5 11.5v6c0 1.52 3.36 2.75 7.5 2.75s7.5-1.23 7.5-2.75v-6"/>',
  settings:
    '<path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h9M17 17h3"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="17" r="2"/>',
  sun:
    '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M18.7 5.3l-1.4 1.4M6.7 17.3l-1.4 1.4"/>',
  moon:
    '<path d="M20 14.2A8.2 8.2 0 1 1 9.8 4a6.6 6.6 0 0 0 10.2 10.2Z"/>',
  send:
    '<path d="M12 19V5.5"/><path d="M6 11l6-5.5 6 5.5"/>',
  clip:
    '<path d="M20.5 11.5l-8 8a5.03 5.03 0 0 1-7.11-7.11l8.49-8.49a3.35 3.35 0 0 1 4.74 4.74l-8.49 8.49a1.68 1.68 0 0 1-2.37-2.37l7.78-7.78"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  trash:
    '<path d="M4.5 7h15"/><path d="M9.5 7V5.5A1.5 1.5 0 0 1 11 4h2a1.5 1.5 0 0 1 1.5 1.5V7"/><path d="M6.5 7l.8 11.2A2 2 0 0 0 9.3 20h5.4a2 2 0 0 0 2-1.8L17.5 7"/><path d="M10 11v5M14 11v5"/>',
  edit:
    '<path d="M4 20h4.5L20 8.5a2.27 2.27 0 0 0-3.2-3.2L5.5 16.8 4 20Z"/><path d="M14.5 7.5l2.5 2.5"/>',
  upload:
    '<path d="M12 15.5V4.5"/><path d="M7.5 9L12 4.5 16.5 9"/><path d="M4.5 15.5v2.5A1.5 1.5 0 0 0 6 19.5h12a1.5 1.5 0 0 0 1.5-1.5v-2.5"/>',
  rebuild:
    '<path d="M20.5 11.5A8.5 8.5 0 1 0 19 16.9"/><path d="M20.5 4.5v5h-5"/>',
  'arrow-left': '<path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/>',
  file:
    '<path d="M13.5 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8.5l-5-5Z"/><path d="M13.5 3.5v5h5"/>',
  x: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  check: '<path d="M5 12.8l4.4 4.4L19 7.4"/>',
  copy:
    '<rect x="9" y="9" width="10.5" height="10.5" rx="2"/><path d="M5.5 14.5h-1a1.5 1.5 0 0 1-1.5-1.5V5a1.5 1.5 0 0 1 1.5-1.5H13A1.5 1.5 0 0 1 14.5 5v1"/>',
  stop: '<rect x="6.75" y="6.75" width="10.5" height="10.5" rx="2.5" fill="currentColor" stroke="none"/>',
  'chevron-down': '<path d="M6.5 9.5l5.5 5.5 5.5-5.5"/>',
  spark:
    '<path d="M12 3.5v17"/><path d="M4.6 7.75l14.8 8.5"/><path d="M19.4 7.75L4.6 16.25"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  alert:
    '<path d="M12 4.25L2.88 19.5h18.24L12 4.25Z"/><path d="M12 10.5v3.5"/><path d="M12 17.2h.01" stroke-width="2.6"/>',
  more: '<path d="M12 5.5h.01M12 12h.01M12 18.5h.01" stroke-width="3.2"/>',
  cpu:
    '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/><rect x="10" y="10" width="4" height="4" rx="1"/><path d="M9 3.5v3M15 3.5v3M9 17.5v3M15 17.5v3M3.5 9h3M3.5 15h3M17.5 9h3M17.5 15h3"/>',
  refresh:
    '<path d="M20.5 11.5A8.5 8.5 0 1 0 19 16.9"/><path d="M20.5 4.5v5h-5"/>',
}

const props = withDefaults(
  defineProps<{ name: keyof typeof ICONS | string; size?: number; strokeWidth?: number }>(),
  { size: 18, strokeWidth: 1.6 },
)

const markup = computed(() => ICONS[props.name] ?? '')
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="markup"
  />
</template>
