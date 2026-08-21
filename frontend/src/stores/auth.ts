import { create } from 'zustand'
import type { UserProfile } from '@/types'

interface AuthState {
  accessToken: string | null
  user: UserProfile | null
  isAuthenticated: boolean
  isAdmin: boolean
  isLoading: boolean
  setToken: (token: string) => void
  setUser: (user: UserProfile) => void
  logout: () => void
  init: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: localStorage.getItem('kayan_access_token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('kayan_access_token'),
  isAdmin: false,
  isLoading: false,

  setToken: (token: string) => {
    localStorage.setItem('kayan_access_token', token)
    set({ accessToken: token, isAuthenticated: true })
  },

  setUser: (user: UserProfile) => {
    set({ user, isAdmin: user.role === 'admin', isLoading: false })
  },

  logout: () => {
    localStorage.removeItem('kayan_access_token')
    set({ accessToken: null, user: null, isAuthenticated: false, isAdmin: false, isLoading: false })
    window.location.href = '/login'
  },

  init: () => {
    const token = localStorage.getItem('kayan_access_token')
    set({ accessToken: token, isAuthenticated: !!token, isLoading: false })
  },
}))
