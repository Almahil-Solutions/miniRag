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
  })
}
