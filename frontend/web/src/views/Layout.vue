<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'

const router = useRouter()
const route = useRoute()
const settingsStore = useSettingsStore()
const collapsed = ref(false)

const navItems = [
  { path: '/chat', label: '对话', icon: 'Chatbubbles' },
  { path: '/knowledge', label: '知识库', icon: 'Document' },
  { path: '/settings', label: '设置', icon: 'Settings' },
]

const currentPath = computed(() => route.path)

function navigate(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-diamond">◆</span>
          <span class="logo-text" v-show="!collapsed">baizeOS</span>
        </div>
      </div>
      <nav class="sidebar-nav">
        <div
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: currentPath === item.path }"
          @click="navigate(item.path)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label" v-show="!collapsed">{{ item.label }}</span>
        </div>
      </nav>
      <div class="sidebar-footer">
        <button class="theme-toggle" @click="settingsStore.toggleTheme()">
          <span class="nav-icon">{{ settingsStore.theme === 'light' ? '☀️' : '🌙' }}</span>
          <span class="nav-label" v-show="!collapsed">{{ settingsStore.theme === 'light' ? '浅色' : '深色' }}</span>
        </button>
      </div>
    </aside>

    <!-- Main -->
    <div class="main-content">
      <header class="topbar">
        <button class="collapse-btn" @click="collapsed = !collapsed">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        <h2 class="topbar-title">
          {{ navItems.find((i) => i.path === route.path)?.label || 'baizeOS' }}
        </h2>
      </header>
      <div class="view-container">
        <RouterView />
      </div>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  width: 100%;
  height: 100%;
}

.sidebar {
  width: 260px;
  min-width: 260px;
  background: var(--bg-primary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal), min-width var(--transition-normal);
}

.sidebar.collapsed {
  width: 60px;
  min-width: 60px;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-diamond {
  font-size: 20px;
  color: var(--accent);
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background var(--transition-fast);
  color: var(--text-secondary);
  font-size: 14px;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
}

.nav-item:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-light);
  color: var(--accent);
  font-weight: 500;
}

.nav-icon {
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border);
}

.theme-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 14px;
  width: 100%;
  transition: all var(--transition-fast);
}

.theme-toggle:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.topbar {
  height: 52px;
  min-height: 52px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-primary);
}

.collapse-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.topbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.view-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
