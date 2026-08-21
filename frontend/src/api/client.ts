import axios from 'axios'

// In production, when served via the Nginx gateway, use relative paths (empty string).
// In local development, if VITE_API_BASE_URL is unset, use the local backend.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? '' : 'http://localhost:8000')

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('kayan_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('kayan_access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
