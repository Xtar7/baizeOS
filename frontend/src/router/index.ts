import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/Layout.vue'),
      children: [
        { path: '', name: 'chat', component: () => import('@/views/ChatView.vue') },
        { path: 'kb', name: 'kb', component: () => import('@/views/KnowledgeView.vue') },
        { path: 'kb/:kbId', name: 'kb-detail', component: () => import('@/views/KbDetailView.vue'), props: true },
        { path: 'settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
