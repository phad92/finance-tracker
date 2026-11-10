<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <header class="h-16 border-b border-border bg-[#090d16]/80 backdrop-blur-md sticky top-0 z-20 px-8 flex items-center justify-between">
    <!-- Quick Search / Command Pill -->
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-400 w-64 cursor-pointer hover:border-slate-700 transition-colors">
        <Search class="w-3.5 h-3.5 text-slate-500" />
        <span>Search assets, tickers...</span>
        <kbd class="ml-auto text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 border border-slate-700 font-mono">⌘K</kbd>
      </div>
    </div>

    <!-- Right Actions -->
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3 py-1 rounded-full text-xs font-mono text-slate-300">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>Base Currency: {{ authStore.user?.default_currency || 'GHS' }}</span>
      </div>
    </div>
  </header>
</template>
