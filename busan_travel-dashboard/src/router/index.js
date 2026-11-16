import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'main', component: () => import('@/views/MapView.vue') },
    { path: '/board', name: 'board-list', component: () => import('@/views/BoardListView.vue') },
    { path: '/board/:id', name: 'board-detail', component: () => import('@/views/BoardDetailView.vue') },
    { path: '/board/write/:id?', name: 'board-write', component: () => import('@/views/BoardWriteView.vue') },
  ],
})

export default router