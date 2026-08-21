import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import type { LoginRequest, RegisterRequest } from '@/types'

export function useAuthInit() {
  const setUser = useAuthStore((s) => s.setUser)

  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const { data } = await authApi.getMe()
      setUser(data)
      return data
    },
    enabled: useAuthStore.getState().isAuthenticated,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useLogin() {
  const setToken = useAuthStore((s) => s.setToken)
  const setUser = useAuthStore((s) => s.setUser)
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      const { data: tokenData } = await authApi.login(data)
      setToken(tokenData.access_token)
      const { data: user } = await authApi.getMe()
      setUser(user)
      return user
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useRegister() {
  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
  })
}

export function useLogout() {
  const logout = useAuthStore((s) => s.logout)
  return useMutation({
    mutationFn: () => authApi.logout({}),
    onSettled: () => logout(),
  })
}
