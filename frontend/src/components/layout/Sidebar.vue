<script setup lang="ts">
import { useRoute } from 'vue-router'
import {
  LayoutDashboard,
  Wallet,
  PieChart,
  Globe,
  TrendingUp,
  BrainCircuit,
  Bot,
  ShieldAlert,
  Landmark,
  LogOut,
  Sparkles,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'My Wealth', href: '/wealth', icon: Wallet },
  { name: 'Portfolios', href: '/portfolios', icon: PieChart },
  { name: 'Markets', href: '/markets', icon: Globe },
  { name: 'Forecasting', href: '/forecasting', icon: TrendingUp },
  { name: 'Research & Macro', href: '/intelligence', icon: BrainCircuit },
  { name: 'Options & Risk', href: '/options', icon: ShieldAlert },
  { name: 'Pensions', href: '/pensions', icon: Landmark },
  { name: 'AI Assistant', href: '/assistant', icon: Bot },
]
</script>

<template>
  <aside class="w-64 border-r border-sidebar-border bg-sidebar flex flex-col h-screen fixed left-0 top-0 z-30 transition-colors duration-200">
    <!-- Brand Header -->
    <div class="h-16 flex items-center px-6 border-b border-sidebar-border gap-3">
      <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
        <Sparkles class="w-5 h-5 text-white" />
      </div>
      <div>
        <h1 class="font-bold text-sm tracking-wide text-slate-900 dark:text-white leading-tight">ANTIGRAVITY</h1>
        <p class="text-[10px] text-slate-500 dark:text-slate-400 font-mono">WEALTH INTELLIGENCE</p>
      </div>
    </div>

    <!-- Navigation Links -->
    <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
      <router-link
        v-for="item in navigation"
        :key="item.name"
        :to="item.href"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
        :class="[
          route.path.startsWith(item.href)
            ? 'bg-blue-600/10 dark:bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25 dark:border-blue-500/20 font-semibold'
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/40'
        ]"
      >
        <component :is="item.icon" class="w-4 h-4" />
        {{ item.name }}
      </router-link>
    </nav>

    <!-- User / Footer -->
    <div class="p-4 border-t border-sidebar-border">
      <div class="flex items-center justify-between">
        <div class="truncate pr-2">
          <p class="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">{{ authStore.user?.full_name || authStore.user?.email }}</p>
          <span class="inline-flex items-center text-[10px] text-slate-500 dark:text-slate-400 font-mono">
            {{ authStore.user?.default_currency || 'GHS' }} Active
          </span>
        </div>
        <button
          @click="authStore.logout"
          title="Sign out"
          class="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <LogOut class="w-4 h-4" />
        </button>
      </div>
    </div>
  </aside>
</template>

