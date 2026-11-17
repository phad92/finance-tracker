<script setup lang="ts">
import { ref } from 'vue'
import { Send, Bot, User, Wrench, Sparkles } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import api from '@/services/api'

interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  tools_invoked?: string[]
  model_used?: string
}

const messages = ref<ChatMsg[]>([
  {
    role: 'assistant',
    content:
      'Hello! I am your Wealth Intelligence Assistant. Ask me about your net worth, currency exposure, portfolio performance, or Ghana & US macroeconomic conditions.',
    tools_invoked: [],
    model_used: 'system',
  },
])
const inputPrompt = ref('')
const conversationId = ref<string | null>(null)
const sending = ref(false)

const quickPrompts = [
  'What is my current net worth and currency exposure?',
  'Summarize my investment portfolios and unrealized P&L',
  'What are the latest Ghana and US macroeconomic indicators?',
]

async function sendMessage(text?: string) {
  const promptText = (text ?? inputPrompt.value).trim()
  if (!promptText || sending.value) return

  messages.value.push({ role: 'user', content: promptText })
  if (!text) inputPrompt.value = ''
  sending.value = true

  try {
    const res = await api.post('/intelligence/assistant/chat', {
      message: promptText,
      conversation_id: conversationId.value,
    })
    conversationId.value = res.data.conversation_id
    messages.value.push({
      role: 'assistant',
      content: res.data.reply,
      tools_invoked: res.data.tools_invoked,
      model_used: res.data.model_used,
    })
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: 'Unable to reach the assistant backend. Please check your connection or session.',
    })
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="max-w-5xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      <!-- Header -->
      <div class="mb-4 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Sparkles class="w-5 h-5 text-blue-400" />
            <span>AI Financial Assistant</span>
          </h1>
          <p class="text-xs text-slate-400">
            Strictly scoped to your authenticated portfolio and wealth ledger via authorized backend tools
          </p>
        </div>
      </div>

      <!-- Quick Prompt Chips -->
      <div class="flex flex-wrap gap-2 mb-4">
        <button
          v-for="qp in quickPrompts"
          :key="qp"
          @click="sendMessage(qp)"
          class="text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-full transition-colors"
        >
          {{ qp }}
        </button>
      </div>

      <!-- Chat Thread -->
      <div class="flex-1 bg-card border border-border rounded-xl p-6 overflow-y-auto space-y-4">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="flex gap-3"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            v-if="msg.role === 'assistant'"
            class="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center shrink-0 mt-1"
          >
            <Bot class="w-4 h-4 text-blue-400" />
          </div>

          <div
            class="max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap"
            :class="
              msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-900/90 border border-slate-800 text-slate-200'
            "
          >
            <div>{{ msg.content }}</div>

            <div
              v-if="msg.tools_invoked && msg.tools_invoked.length > 0"
              class="mt-3 pt-2 border-t border-slate-800 flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-400"
            >
              <span class="flex items-center gap-1 text-emerald-400">
                <Wrench class="w-3 h-3" /> Tools:
              </span>
              <span
                v-for="t in msg.tools_invoked"
                :key="t"
                class="bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700"
              >
                {{ t }}
              </span>
              <span v-if="msg.model_used" class="ml-auto text-slate-500">{{ msg.model_used }}</span>
            </div>
          </div>

          <div
            v-if="msg.role === 'user'"
            class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-1"
          >
            <User class="w-4 h-4 text-slate-300" />
          </div>
        </div>

        <div v-if="sending" class="flex items-center gap-2 text-xs text-slate-400 font-mono pl-11">
          <span class="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
          <span>Querying authorized wealth tools...</span>
        </div>
      </div>

      <!-- Input Bar -->
      <form @submit.prevent="sendMessage()" class="mt-4 flex gap-3">
        <input
          v-model="inputPrompt"
          type="text"
          placeholder="Ask about your net worth, portfolio returns, currency risk, or macro outlook..."
          class="flex-1 bg-card border border-border rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          :disabled="sending || !inputPrompt.trim()"
          class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium px-5 py-3 rounded-xl text-sm flex items-center gap-2 transition-colors shadow-lg shadow-blue-600/20"
        >
          <Send class="w-4 h-4" />
          <span>Send</span>
        </button>
      </form>
    </div>
  </AppLayout>
</template>

