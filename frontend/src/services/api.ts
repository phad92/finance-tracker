import axios from 'axios'

// Keep access token strictly in memory (never in localStorage) to prevent XSS token exfiltration.
// Refresh token is managed via an HttpOnly cookie sent automatically with withCredentials: true.
let inMemoryAccessToken: string | null = null

export function setInMemoryAccessToken(token: string | null) {
  inMemoryAccessToken = token
}

export function getInMemoryAccessToken(): string | null {
  return inMemoryAccessToken
}

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to inject Authorization header from memory
api.interceptors.request.use((config) => {
  if (inMemoryAccessToken) {
    config.headers.Authorization = `Bearer ${inMemoryAccessToken}`
  }
  return config
})

let refreshPromise: Promise<string | null> | null = null

// Response interceptor: attempt silent cookie refresh on 401 before redirecting to /login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (
      error.response &&
      error.response.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !String(originalRequest.url || '').includes('/auth/login') &&
      !String(originalRequest.url || '').includes('/auth/refresh')
    ) {
      originalRequest._retry = true
      try {
        if (!refreshPromise) {
          refreshPromise = api
            .post('/auth/refresh')
            .then((res) => {
              const nextToken = res.data?.access_token ?? null
              setInMemoryAccessToken(nextToken)
              return nextToken
            })
            .catch(() => {
              setInMemoryAccessToken(null)
              return null
            })
            .finally(() => {
              refreshPromise = null
            })
        }
        const nextToken = await refreshPromise
        if (nextToken) {
          originalRequest.headers.Authorization = `Bearer ${nextToken}`
          return api(originalRequest)
        }
      } catch {
        setInMemoryAccessToken(null)
      }

      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
