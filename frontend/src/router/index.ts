import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import WealthView from '@/views/WealthView.vue'
import PortfolioView from '@/views/PortfolioView.vue'
import ForecastingView from '@/views/ForecastingView.vue'
import MarketsView from '@/views/MarketsView.vue'
import IntelligenceView from '@/views/IntelligenceView.vue'
import AssistantView from '@/views/AssistantView.vue'
import OptionsRiskView from '@/views/OptionsRiskView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true },
    },
    {
      path: '/wealth',
      name: 'wealth',
      component: WealthView,
      meta: { requiresAuth: true },
    },
    {
      path: '/portfolios',
      name: 'portfolios',
      component: PortfolioView,
      meta: { requiresAuth: true },
    },
    {
      path: '/markets',
      name: 'markets',
      component: MarketsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/forecasting',
      name: 'forecasting',
      component: ForecastingView,
      meta: { requiresAuth: true },
    },
    {
      path: '/intelligence',
      name: 'intelligence',
      component: IntelligenceView,
      meta: { requiresAuth: true },
    },
    {
      path: '/assistant',
      name: 'assistant',
      component: AssistantView,
      meta: { requiresAuth: true },
    },
    {
      path: '/options',
      name: 'options',
      component: OptionsRiskView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login' })
  } else if (to.meta.guestOnly && authStore.isAuthenticated) {
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router

