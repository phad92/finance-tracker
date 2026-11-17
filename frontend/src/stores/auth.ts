import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export interface User {
  id: string
  email: string
  full_name?: string
  default_currency: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(formData: URLSearchParams) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      token.value = res.data.access_token
      localStorage.setItem('access_token', res.data.access_token)
      localStorage.setItem('refresh_token', res.data.refresh_token)
      await fetchMe()
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to authenticate'
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(payload: { email: string; password: string; full_name?: string; default_currency?: string }) {
    loading.value = true
    error.value = null
    try {
      await api.post('/auth/register', payload)
      // Auto login after registration
      const params = new URLSearchParams()
      params.append('username', payload.email)
      params.append('password', payload.password)
      return await login(params)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Registration failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const res = await api.get<User>('/auth/me')
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    fetchMe,
    logout,
  }
})

