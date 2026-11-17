<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'

const authStore = useAuthStore()
</script>

<template>
  <header class="h-16 border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-20 px-8 flex items-center justify-between transition-colors duration-200">
    <!-- Quick Search / Command Pill -->
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-1.5 text-xs text-slate-500 dark:text-slate-400 w-64 cursor-pointer hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
        <Search class="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
        <span>Search assets, tickers...</span>
        <kbd class="ml-auto text-[10px] bg-muted px-1.5 py-0.5 rounded text-slate-500 dark:text-slate-400 border border-border font-mono">⌘K</kbd>
      </div>
    </div>

    <!-- Right Actions -->
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2 bg-card border border-border px-3 py-1.5 rounded-full text-xs font-mono text-slate-700 dark:text-slate-300">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>Base Currency: {{ authStore.user?.default_currency || 'GHS' }}</span>
      </div>
      <ThemeToggle />
    </div>
  </header>
</template>
