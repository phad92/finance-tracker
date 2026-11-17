<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Sparkles, ArrowRight, Lock, Mail, User as UserIcon } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isRegister = ref(false)
const email = ref('')
const password = ref('')
const fullName = ref('')
const defaultCurrency = ref('GHS')

async function handleSubmit() {
  if (isRegister.value) {
    const success = await authStore.register({
      email: email.value,
      password: password.value,
      full_name: fullName.value || undefined,
      default_currency: defaultCurrency.value,
    })
    if (success) router.push('/dashboard')
  } else {
    const params = new URLSearchParams()
    params.append('username', email.value)
    params.append('password', password.value)
    const success = await authStore.login(params)
    if (success) router.push('/dashboard')
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#070b14] flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-card border border-border rounded-2xl p-8 shadow-2xl relative overflow-hidden">
      <!-- Glow Effect -->
      <div class="absolute -top-24 -right-24 w-48 h-48 bg-blue-600/20 rounded-full blur-3xl pointer-events-none"></div>

      <!-- Header -->
      <div class="text-center mb-8">
        <div class="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20 mx-auto mb-4">
          <Sparkles class="w-6 h-6 text-white" />
        </div>
        <h2 class="text-2xl font-bold text-white tracking-tight">
          {{ isRegister ? 'Create Your Account' : 'Welcome to Wealth Intelligence' }}
        </h2>
        <p class="text-sm text-slate-400 mt-1">
          {{ isRegister ? 'Personal multi-currency financial tracking' : 'Sign in to access your portfolios and net worth' }}
        </p>
      </div>

      <!-- Error Alert -->
      <div v-if="authStore.error" class="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
        {{ authStore.error }}
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div v-if="isRegister">
          <label class="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
          <div class="relative">
            <UserIcon class="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              v-model="fullName"
              type="text"
              placeholder="Kwame Mensah"
              class="w-full bg-slate-900 border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
          <div class="relative">
            <Mail class="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              v-model="email"
              type="email"
              required
              placeholder="you@domain.com"
              class="w-full bg-slate-900 border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
          <div class="relative">
            <Lock class="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              v-model="password"
              type="password"
              required
              minlength="8"
              placeholder="••••••••"
              class="w-full bg-slate-900 border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div v-if="isRegister">
          <label class="block text-xs font-medium text-slate-300 mb-1.5">Default Reporting Currency</label>
          <select
            v-model="defaultCurrency"
            class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="GHS">GHS (Ghana Cedi - GH₵)</option>
            <option value="USD">USD (US Dollar - $)</option>
            <option value="GBP">GBP (British Pound - £)</option>
            <option value="EUR">EUR (Euro - €)</option>
          </select>
        </div>

        <button
          type="submit"
          :disabled="authStore.loading"
          class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg text-sm transition-colors flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 mt-6"
        >
          <span>{{ isRegister ? 'Register Account' : 'Sign In' }}</span>
          <ArrowRight class="w-4 h-4" />
        </button>
      </form>

      <!-- Toggle Mode -->
      <div class="mt-6 text-center">
        <button
          @click="isRegister = !isRegister"
          type="button"
          class="text-xs text-slate-400 hover:text-blue-400 transition-colors"
        >
          {{ isRegister ? 'Already have an account? Sign in' : "Don't have an account? Create one" }}
        </button>
      </div>
    </div>
  </div>
</template>

