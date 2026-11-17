import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'finance_theme'

export const useThemeStore = defineStore('theme', () => {
  const saved = (localStorage.getItem(STORAGE_KEY) as ThemeMode | null) || 'dark'
  const theme = ref<ThemeMode>(saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'dark')

  const mediaQuery =
    typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)') : null
  const systemPrefersDark = ref<boolean>(mediaQuery ? mediaQuery.matches : true)

  let initialized = false

  const isDark = computed(() => {
    if (theme.value === 'system') return systemPrefersDark.value
    return theme.value === 'dark'
  })

  function applyThemeToDom() {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    if (isDark.value) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) {
      meta.setAttribute('content', isDark.value ? '#0f172a' : '#f8fafc')
    }
  }

  function setTheme(mode: ThemeMode) {
    theme.value = mode
    localStorage.setItem(STORAGE_KEY, mode)
    applyThemeToDom()
  }

  function cycleTheme() {
    const order: ThemeMode[] = ['dark', 'light', 'system']
    const next = order[(order.indexOf(theme.value) + 1) % order.length]
    setTheme(next)
  }

  function initTheme() {
    if (!initialized && mediaQuery) {
      initialized = true
      mediaQuery.addEventListener('change', (e) => {
        systemPrefersDark.value = e.matches
        if (theme.value === 'system') {
          applyThemeToDom()
        }
      })
    }
    applyThemeToDom()
  }

  return {
    theme,
    isDark,
    setTheme,
    cycleTheme,
    initTheme,
  }
})
