<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Sun, Moon, Monitor, Check } from 'lucide-vue-next'
import { useThemeStore, type ThemeMode } from '@/stores/theme'

const themeStore = useThemeStore()
const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const options: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

function selectTheme(mode: ThemeMode) {
  themeStore.setTheme(mode)
  isOpen.value = false
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isOpen.value) {
    isOpen.value = false
  }
}

function handlePointerDown(e: PointerEvent) {
  if (!isOpen.value) return
  const target = e.target as Node | null
  if (containerRef.value && target && !containerRef.value.contains(target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  themeStore.initTheme()
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('pointerdown', handlePointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('pointerdown', handlePointerDown)
})
</script>

<template>
  <div ref="containerRef" class="relative">
    <button
      type="button"
      :aria-expanded="isOpen"
      aria-haspopup="menu"
      aria-label="Switch color theme"
      @click="isOpen = !isOpen"
      class="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-border bg-card hover:bg-muted text-xs font-medium text-slate-700 dark:text-slate-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <Sun v-if="themeStore.theme === 'light'" class="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
      <Moon v-else-if="themeStore.theme === 'dark'" class="w-3.5 h-3.5 text-blue-400" aria-hidden="true" />
      <Monitor v-else class="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
      <span class="capitalize hidden sm:inline">{{ themeStore.theme }}</span>
    </button>

    <div
      v-if="isOpen"
      role="menu"
      aria-label="Color theme options"
      class="absolute right-0 mt-2 w-36 rounded-xl border border-border bg-card p-1 shadow-xl z-50"
    >
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        role="menuitemradio"
        :aria-checked="themeStore.theme === opt.value"
        @click="selectTheme(opt.value)"
        class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
        :class="
          themeStore.theme === opt.value
            ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
            : 'text-slate-700 dark:text-slate-300 hover:bg-muted'
        "
      >
        <span class="flex items-center gap-2">
          <component :is="opt.icon" class="w-3.5 h-3.5" aria-hidden="true" />
          <span>{{ opt.label }}</span>
        </span>
        <Check v-if="themeStore.theme === opt.value" class="w-3.5 h-3.5" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
