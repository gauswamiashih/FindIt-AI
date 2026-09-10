/**
 * Axios API Service
 * Attaches Supabase JWT Bearer token and handles 401 response errors.
 */

import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  withCredentials: true,
  timeout: 30000,
})

// ─── Request Interceptor ───────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ─── Response Interceptor ──────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status

    // On 401 Unauthorized from FastAPI, clear invalid state
    if (status === 401 && !error.config?.url?.includes('/auth/me')) {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('user')
    }

    return Promise.reject(error)
  }
)

export default api
