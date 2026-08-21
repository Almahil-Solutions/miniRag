import { useMutation, useQuery } from '@tanstack/react-query'
import { nlpApi, streamAnswer } from '@/api/nlp'
import type { PushRequest, SearchRequest } from '@/types'

export function usePushIndex(projectUuid: string) {
  return useMutation({
    mutationFn: (data: PushRequest) => nlpApi.pushIndex(projectUuid, data),
  })
}

export function useIndexInfo(projectUuid: string) {
  return useQuery({
    queryKey: ['index', projectUuid],
    queryFn: async () => {
      const { data } = await nlpApi.getIndexInfo(projectUuid)
      return data
    },
    enabled: !!projectUuid,
  })
}

export function useSearch(projectUuid: string) {
  return useMutation({
    mutationFn: (data: SearchRequest) => nlpApi.search(projectUuid, data),
  })
}

export function useAnswer(projectUuid: string) {
  return useMutation({
    mutationFn: (data: SearchRequest) => nlpApi.answer(projectUuid, data),
  })
}

export function useStreamAnswer() {
  return useMutation({
    mutationFn: async ({
      projectUuid,
      data,
      onChunk,
    }: {
      projectUuid: string
      data: SearchRequest
      onChunk: (chunk: string) => void
    }) => {
      await streamAnswer(projectUuid, data, onChunk)
    },
  })
}

export function useQueryHistory(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['history', page, pageSize],
    queryFn: async () => {
      const { data } = await nlpApi.getHistory(page, pageSize)
      return data
    },
  })
}
