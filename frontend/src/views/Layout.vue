<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'

const router = useRouter()
const route = useRoute()
const settingsStore = useSettingsStore()

// Sidebar state
const sidebarOpen = ref(true)
const mobileDrawerOpen = ref(false)

// Detect mobile viewport
const isMobile = ref(false)
function checkMobile() {
  isMobile.value = window.innerWidth < 768
}
checkMobile()
window.addEventListener('resize', checkMobile)

// Close drawer on navigation
watch(() => route.path, () => {
  mobileDrawerOpen.value = false
})

const navItems = [
  { path: '/chat', label: '对话', icon: 'Chatbubbles' },
  { path: '/knowledge', label: '知识库', icon: 'Document' },
  { path: '/settings', label: '设置', icon: 'Settings' },
]

const currentPath = computed(() => route.path)

function navigate(path: string) {
  router.push(path)
  mobileDrawerOpen.value = false
}

function toggleSidebar() {
  if (isMobile.value) {
    mobileDrawerOpen.value = !mobileDrawerOpen.value
  } else {
    sidebarOpen.value = !sidebarOpen.value
  }
}
</script>

<template>
  <div class="layout">
    <!-- Mobile overlay backdrop -->
    <Transition name="drawer-fade">
      <div
        v-if="isMobile && mobileDrawerOpen"
        class="drawer-backdrop"
        @click="mobileDrawerOpen = false"
      />
    </Transition>

    <!-- Sidebar / Drawer -->
    <aside
      class="sidebar"
      :class="[
        { 'sidebar--collapsed': !sidebarOpen && !isMobile },
        { 'sidebar--mobile-open': isMobile && mobileDrawerOpen },
      ]"
    >
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-diamond">◆</span>
          <span class="logo-text" :class="{ 'logo-text--hidden': !sidebarOpen && !isMobile }">baizeOS</span>
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
          <span class="nav-label" :class="{ 'nav-label--hidden': !sidebarOpen && !isMobile }">{{ item.label }}</span>
        </div>
      </nav>

      <div class="sidebar-footer">
        <button class="theme-toggle" @click="settingsStore.toggleTheme()">
          <span class="nav-icon">{{ settingsStore.theme === 'light' ? '☀️' : '🌙' }}</span>
          <span class="nav-label" :class="{ 'nav-label--hidden': !sidebarOpen && !isMobile }">
            {{ settingsStore.theme === 'light' ? '浅色' : '深色' }}
          </span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-content">
      <header class="topbar">
        <button class="collapse-btn" @click="toggleSidebar" aria-label="Toggle sidebar">
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

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--bg-primary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal), min-width var(--transition-normal), transform var(--transition-normal);
  z-index: 100;
  position: relative;
}

.sidebar--collapsed {
  width: var(--sidebar-collapsed);
  min-width: var(--sidebar-collapsed);
}

/* Mobile drawer */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 280px;
    min-width: 280px;
    transform: translateX(-100%);
    box-shadow: none;
  }

  .sidebar--mobile-open {
    transform: translateX(0);
    box-shadow: var(--shadow-lg);
  }

  .sidebar--collapsed {
    width: 280px;
    min-width: 280px;
  }
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
  transition: opacity var(--transition-fast);
}

.logo-text--hidden {
  opacity: 0;
  width: 0;
  overflow: hidden;
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
  white-space: nowrap;
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

.nav-label {
  transition: opacity var(--transition-fast);
}

.nav-label--hidden {
  opacity: 0;
  width: 0;
  overflow: hidden;
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

/* Main content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.topbar {
  height: var(--topbar-height);
  min-height: var(--topbar-height);
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
  transition: all var(--transition-fast);
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

/* Drawer fade transition */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity var(--transition-normal);
}

.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 99;
}

/* Mobile: hide sidebar when closed, show topbar icon */
@media (max-width: 768px) {
  .view-container {
    padding: 16px;
  }

  .topbar {
    padding: 0 14px;
  }
}
</style>
