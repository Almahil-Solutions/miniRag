import { api } from './client'
import type {
  AdminUserListResponse,
  AdminUpdateUserRequest,
  AdminQueryLogResponse,
} from '@/types'

export const adminApi = {
  listUsers: (page = 1, pageSize = 20) =>
    api.get<AdminUserListResponse>('/api/v1/admin/users', { params: { page, page_size: pageSize } }),

  updateUser: (userId: string, data: AdminUpdateUserRequest) =>
    api.patch(`/api/v1/admin/users/${userId}`, data),

  listQueryLogs: (page = 1, pageSize = 50) =>
    api.get<AdminQueryLogResponse>('/api/v1/admin/query-logs', { params: { page, page_size: pageSize } }),
}
