import { api } from './client'
import type {
  UserProfile,
  UpdateProfileRequest,
  ApiKey,
  CreateApiKeyRequest,
} from '@/types'

export const usersApi = {
  getMe: () => api.get<UserProfile>('/api/v1/users/me'),

  updateMe: (data: UpdateProfileRequest) =>
    api.patch<UserProfile>('/api/v1/users/me', data),

  createApiKey: (data: CreateApiKeyRequest) =>
    api.post<ApiKey>('/api/v1/users/me/api-keys', data),

  revokeApiKey: (keyId: string) =>
    api.delete(`/api/v1/users/me/api-keys/${keyId}`),
}
