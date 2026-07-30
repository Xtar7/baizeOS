import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/Layout.vue'),
      redirect: '/chat',
      children: [
        { path: 'chat', name: 'Chat', component: () => import('@/views/ChatView.vue') },
        { path: 'knowledge', name: 'Knowledge', component: () => import('@/views/KnowledgeView.vue') },
        { path: 'knowledge/:id', name: 'KbDetail', component: () => import('@/views/KbDetailView.vue') },
        { path: 'settings', name: 'Settings', component: () => import('@/views/SettingsView.vue') },
      ],
    },
  ],
})

export default router
