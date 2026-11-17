<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { Info } from 'lucide-vue-next'

interface Props {
  label: string
  title?: string
  content: string
  meta?: string
  sourceUrl?: string | null
  sourceName?: string
  align?: 'center' | 'end'
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  meta: undefined,
  sourceUrl: null,
  sourceName: undefined,
  align: 'center',
})

const tooltipId = `tt-${useId()}`
const containerRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLButtonElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)

const isHovered = ref(false)
const isFocused = ref(false)
const isPinned = ref(false)
const dismissedUntilBlur = ref(false)

const placement = ref<'top' | 'bottom'>('top')
const panelCoords = ref<{ top: number; left: number; arrowLeft: number }>({
  top: 0,
  left: 0,
  arrowLeft: 140,
})

let closeTimer: ReturnType<typeof setTimeout> | null = null

const isOpen = computed(
  () => isPinned.value || (!dismissedUntilBlur.value && (isHovered.value || isFocused.value)),
)

const clearCloseTimer = () => {
  if (closeTimer) {
    clearTimeout(closeTimer)
    closeTimer = null
  }
}

const updatePosition = async () => {
  await nextTick()
  const trigger = triggerRef.value
  const panel = panelRef.value
  if (!trigger || !panel) return

  const rect = trigger.getBoundingClientRect()
  const panelRect = panel.getBoundingClientRect()
  const gap = 8
  const viewportPad = 12

  const fitsAbove = rect.top - panelRect.height - gap >= viewportPad
  placement.value = fitsAbove ? 'top' : 'bottom'

  const top = fitsAbove
    ? rect.top - panelRect.height - gap
    : Math.min(window.innerHeight - panelRect.height - viewportPad, rect.bottom + gap)

  const idealLeft =
    props.align === 'end'
      ? rect.right - panelRect.width
      : rect.left + rect.width / 2 - panelRect.width / 2

  const maxLeft = Math.max(viewportPad, window.innerWidth - panelRect.width - viewportPad)
  const left = Math.min(Math.max(viewportPad, idealLeft), maxLeft)
  const triggerCenterX = rect.left + rect.width / 2
  const arrowLeft = Math.min(Math.max(12, triggerCenterX - left), panelRect.width - 12)

  panelCoords.value = { top, left, arrowLeft }
}

const handleMouseEnter = () => {
  clearCloseTimer()
  dismissedUntilBlur.value = false
  isHovered.value = true
  void updatePosition()
}

const handleMouseLeave = () => {
  clearCloseTimer()
  closeTimer = setTimeout(() => {
    isHovered.value = false
  }, 120)
}

const handleFocusIn = () => {
  clearCloseTimer()
  dismissedUntilBlur.value = false
  isFocused.value = true
  void updatePosition()
}

const handleFocusOut = (e: FocusEvent) => {
  const next = e.relatedTarget as Node | null
  if (containerRef.value && next && containerRef.value.contains(next)) {
    return
  }
  isFocused.value = false
  dismissedUntilBlur.value = false
}

const togglePin = () => {
  dismissedUntilBlur.value = false
  isPinned.value = !isPinned.value
  if (isPinned.value) {
    void updatePosition()
  }
}

const dismiss = () => {
  clearCloseTimer()
  isPinned.value = false
  isHovered.value = false
  dismissedUntilBlur.value = true
}

const handleDocumentKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && isOpen.value) {
    dismiss()
  }
}

const handleDocumentPointerDown = (e: PointerEvent) => {
  if (!isOpen.value) return
  const target = e.target as Node | null
  if (containerRef.value && target && !containerRef.value.contains(target)) {
    isPinned.value = false
    isHovered.value = false
  }
}

const handleViewportChange = () => {
  if (isOpen.value) {
    void updatePosition()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleDocumentKeydown)
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  window.addEventListener('scroll', handleViewportChange, true)
  window.addEventListener('resize', handleViewportChange)
})

onBeforeUnmount(() => {
  clearCloseTimer()
  document.removeEventListener('keydown', handleDocumentKeydown)
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  window.removeEventListener('scroll', handleViewportChange, true)
  window.removeEventListener('resize', handleViewportChange)
})
</script>

<template>
  <span
    ref="containerRef"
    class="relative inline-flex items-center"
    @focusout="handleFocusOut"
  >
    <button
      ref="triggerRef"
      type="button"
      :aria-label="label"
      :aria-expanded="isOpen"
      :aria-controls="tooltipId"
      class="inline-flex items-center justify-center w-5 h-5 rounded-full text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-300 hover:bg-slate-100 dark:hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @focus="handleFocusIn"
      @click.stop="togglePin"
    >
      <Info class="w-3.5 h-3.5" aria-hidden="true" />
    </button>

    <div
      v-if="isOpen"
      :id="tooltipId"
      ref="panelRef"
      role="tooltip"
      :style="{
        top: `${panelCoords.top}px`,
        left: `${panelCoords.left}px`,
      }"
      class="fixed z-50 w-72 max-w-[calc(100vw-24px)] rounded-xl border border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-950/95 backdrop-blur-sm p-3 text-left shadow-xl shadow-slate-900/10 dark:shadow-2xl dark:shadow-black/60 text-xs text-slate-700 dark:text-slate-200 leading-relaxed"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
    >
      <span
        aria-hidden="true"
        :style="{ left: `${panelCoords.arrowLeft}px` }"
        class="absolute -translate-x-1/2 w-2.5 h-2.5 rotate-45 bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-700"
        :class="
          placement === 'top'
            ? '-bottom-[5px] border-r border-b'
            : '-top-[5px] border-l border-t'
        "
      />
      <div v-if="title" class="font-semibold text-slate-900 dark:text-white mb-1">{{ title }}</div>
      <p class="text-slate-600 dark:text-slate-300">{{ content }}</p>
      <div
        v-if="meta || sourceUrl || sourceName"
        class="mt-2 pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400"
      >
        <span v-if="meta" class="font-mono text-slate-500 dark:text-slate-400">{{ meta }}</span>
        <a
          v-if="sourceUrl"
          :href="sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 underline underline-offset-2 truncate ml-auto"
        >
          {{ sourceName || 'Official source' }}
        </a>
        <span v-else-if="sourceName" class="text-slate-500 dark:text-slate-400 truncate ml-auto">{{ sourceName }}</span>
      </div>
    </div>
  </span>
</template>
