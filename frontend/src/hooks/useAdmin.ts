import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '@/api/admin'
import type { AdminUpdateUserRequest } from '@/types'

export function useAdminUsers(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['admin', 'users', page, pageSize],
    queryFn: async () => {
      const { data } = await adminApi.listUsers(page, pageSize)
      return data
    },
  })
}

export function useAdminUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: AdminUpdateUserRequest }) =>
      adminApi.updateUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}

export function useAdminQueryLogs(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ['admin', 'logs', page, pageSize],
    queryFn: async () => {
      const { data } = await adminApi.listQueryLogs(page, pageSize)
      return data
    },
  })
}
