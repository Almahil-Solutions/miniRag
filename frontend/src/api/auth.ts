import { api } from './client'
import type {
  RegisterRequest,
  LoginRequest,
  TokenResponse,
  RefreshRequest,
  LogoutRequest,
  UserProfile,
} from '@/types'

export const authApi = {
  register: (data: RegisterRequest) =>
    api.post<{ user_id: string; email: string; role: string }>('/api/v1/auth/register', data),

  login: (data: LoginRequest) =>
    api.post<TokenResponse>('/api/v1/auth/login', data),

  refresh: (data: RefreshRequest) =>
    api.post<TokenResponse>('/api/v1/auth/refresh', data),

  logout: (data: LogoutRequest) =>
    api.post('/api/v1/auth/logout', data),

  getMe: () => api.get<UserProfile>('/api/v1/users/me'),
}
