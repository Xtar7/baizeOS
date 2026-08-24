<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import SideBar from '@/components/SideBar.vue'
import Icon from '@/ui/Icon.vue'

const route = useRoute()
const drawerOpen = ref(false)

// 路由变化时收起移动端抽屉
watch(
  () => route.fullPath,
  () => {
    drawerOpen.value = false
  },
)
</script>

<template>
  <div class="shell">
    <!-- 移动端顶栏 -->
    <header class="mobile-bar">
      <button class="mobile-bar__menu" type="button" aria-label="打开导航" @click="drawerOpen = true">
        <Icon name="menu" :size="19" />
      </button>
      <span class="mobile-bar__brand">baize<i>OS</i></span>
    </header>

    <!-- 桌面侧边栏 -->
    <SideBar class="desktop-only" />

    <!-- 移动端抽屉 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="drawerOpen" class="drawer-overlay" @click="drawerOpen = false" />
      </Transition>
      <Transition name="drawer">
        <SideBar v-if="drawerOpen" class="drawer-panel" @navigate="drawerOpen = false" />
      </Transition>
    </Teleport>

    <main class="content">
      <RouterView v-slot="{ Component }">
        <Transition name="view" mode="out-in">
          <component :is="Component" :key="route.path" />
        </Transition>
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
.shell {
  height: 100dvh;
  display: flex;
}

.content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.desktop-only {
  display: flex;
}

.mobile-bar {
  display: none;
}

@media (max-width: 880px) {
  .desktop-only {
    display: none;
  }

  .shell {
    flex-direction: column;
  }

  .mobile-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    height: 52px;
    padding: 0 14px;
    background: var(--bg-deep);
    border-bottom: 1px solid var(--line);
    flex-shrink: 0;
  }

  .mobile-bar__menu {
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    border-radius: 9px;
    color: var(--ink-2);
  }

  .mobile-bar__menu:hover {
    background: rgb(28 25 23 / 5%);
  }

  .dark .mobile-bar__menu:hover {
    background: rgb(255 255 255 / 6%);
  }

  .mobile-bar__brand {
    font-family: var(--font-display);
    font-size: 17px;
    color: var(--ink);
  }

  .mobile-bar__brand i {
    font-style: normal;
    color: var(--accent-text);
  }
}

.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: var(--overlay);
}

.drawer-panel {
  position: fixed;
  z-index: 85;
  top: 0;
  left: 0;
  bottom: 0;
}

.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1);
}

.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(-100%);
}
</style>
