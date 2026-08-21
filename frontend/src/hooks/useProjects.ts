import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '@/api/projects'

export function useProjects(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ['projects', page, pageSize],
    queryFn: async () => {
      const { data } = await projectsApi.list(page, pageSize)
      return data
    },
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => projectsApi.create(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (projectUuid: string) => projectsApi.delete(projectUuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}
