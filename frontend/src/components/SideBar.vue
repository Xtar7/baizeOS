<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import Icon from '@/ui/Icon.vue'

const emit = defineEmits<{ (e: 'navigate'): void }>()

const route = useRoute()
const settings = useSettingsStore()

const NAV = [
  { name: 'chat', label: '对话', icon: 'chat', to: '/' },
  { name: 'kb', label: '知识库', icon: 'library', to: '/kb' },
  { name: 'settings', label: '设置', icon: 'settings', to: '/settings' },
] as const

const isChatActive = computed(() => route.name === 'chat')
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar__brand">
      <span class="brand-mark" aria-hidden="true"><Icon name="spark" :size="19" :stroke-width="1.9" /></span>
      <span class="brand-name">baize<i>OS</i></span>
    </div>

    <nav class="sidebar__nav" aria-label="主导航">
      <RouterLink
        v-for="item in NAV"
        :key="item.name"
        :to="item.to"
        class="nav-item"
        :class="{ 'is-active': item.name === 'chat' ? isChatActive : route.name === item.name || route.path.startsWith(item.to) }"
        @click="emit('navigate')"
      >
        <Icon :name="item.icon" :size="17.5" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar__foot">
      <button
        class="theme-toggle"
        type="button"
        :aria-label="settings.isDark ? '切换为浅色模式' : '切换为深色模式'"
        @click="settings.toggleTheme()"
      >
        <Icon :name="settings.isDark ? 'sun' : 'moon'" :size="16" />
        <span>{{ settings.isDark ? '浅色模式' : '深色模式' }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  /* 跟随视口缩放：≥1440px 保持原 264px，小桌面优雅收窄，不低于 232px */
  width: clamp(232px, 18.3vw, 264px);
  flex-shrink: 0;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-deep);
  border-right: 1px solid var(--line);
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 14px;
}

.brand-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--accent);
  color: #fff;
  box-shadow: 0 2px 6px -1px rgb(201 99 66 / 40%);
}

.brand-name {
  font-family: var(--font-display);
  font-size: 19px;
  letter-spacing: 0.01em;
  color: var(--ink);
}

.brand-name i {
  font-style: normal;
  color: var(--accent-text);
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  height: 38px;
  padding: 0 13px;
  border-radius: 10px;
  font-size: 14px;
  color: var(--ink-2);
  transition:
    background-color 0.14s ease-out,
    color 0.14s ease-out;
}

.nav-item:hover {
  background: rgb(28 25 23 / 5%);
  color: var(--ink);
}

.dark .nav-item:hover {
  background: rgb(255 255 255 / 5%);
}

.nav-item.is-active {
  background: var(--surface);
  color: var(--ink);
  font-weight: 500;
  box-shadow:
    inset 0 0 0 1px var(--line-strong),
    0 1px 2px rgb(28 25 23 / 4%);
}

.nav-item.is-active svg {
  color: var(--accent-text);
}

.sidebar__foot {
  margin-top: auto;
  padding: 12px;
  border-top: 1px solid var(--line);
}

.theme-toggle {
  /* 紧凑按钮：只占内容宽度，不再撑满整条 */
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 7px;
  height: 32px;
  padding: 0 11px;
  border-radius: 9px;
  border: 1px solid var(--line-strong);
  background: var(--surface);
  font-size: 13px;
  color: var(--ink-2);
  transition:
    border-color 0.14s ease-out,
    color 0.14s ease-out,
    background-color 0.14s ease-out;
}

.theme-toggle:hover {
  border-color: var(--accent-tint-line);
  color: var(--ink);
}

.theme-toggle svg {
  color: var(--accent-text);
}
</style>
