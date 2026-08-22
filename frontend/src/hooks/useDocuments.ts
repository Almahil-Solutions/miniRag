import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { dataApi } from '@/api/data'
import type { ProcessRequest } from '@/types'

export function useDocuments(projectUuid: string, page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ['documents', projectUuid, page, pageSize],
    queryFn: async () => {
      const { data } = await dataApi.listDocuments(projectUuid, page, pageSize)
      return data
    },
    enabled: !!projectUuid,
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectUuid, file }: { projectUuid: string; file: File }) =>
      dataApi.upload(projectUuid, file),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['documents', vars.projectUuid] })
    },
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectUuid, assetUuid }: { projectUuid: string; assetUuid: string }) =>
      dataApi.deleteDocument(projectUuid, assetUuid),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['documents', vars.projectUuid] })
    },
  })
}

export function useReprocessDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectUuid,
      assetUuid,
      data,
    }: {
      projectUuid: string
      assetUuid: string
      data: ProcessRequest
    }) => dataApi.reprocessDocument(projectUuid, assetUuid, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['documents', vars.projectUuid] })
      queryClient.invalidateQueries({ queryKey: ['index-info', vars.projectUuid] })
    },
  })
}

export function useProcessAndPush() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectUuid,
      data,
    }: {
      projectUuid: string
      data: ProcessRequest
    }) => dataApi.processAndPush(projectUuid, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['documents', vars.projectUuid] })
      queryClient.invalidateQueries({ queryKey: ['index-info', vars.projectUuid] })
    },
  })
}

export function useProcessDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectUuid,
      data,
    }: {
      projectUuid: string
      data: ProcessRequest
    }) => dataApi.process(projectUuid, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['documents', vars.projectUuid] })
    },
  })
}

export function useTaskStatus(taskId: string | null) {
  return useQuery({
    queryKey: ['task-status', taskId],
    queryFn: async () => {
      if (!taskId) return null
      const { data } = await dataApi.getTaskStatus(taskId)
      return data
    },
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && (data.ready || data.status === 'SUCCESS' || data.status === 'FAILURE')) {
        return false
      }
      return 2000
    },
  })
}

