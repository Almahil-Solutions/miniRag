import { api } from './client'
import type {
  PushRequest,
  SearchRequest,
  SearchResponse,
  AnswerResponse,
  IndexInfoResponse,
  QueryLogResponse,
} from '@/types'

export const nlpApi = {
  pushIndex: (projectUuid: string, data: PushRequest) =>
    api.post<{ signal: string; task_id: string }>(`/api/v1/nlp/index/push/${projectUuid}`, data),

  getIndexInfo: (projectUuid: string) =>
    api.get<IndexInfoResponse>(`/api/v1/nlp/index/info/${projectUuid}`),

  search: (projectUuid: string, data: SearchRequest) =>
    api.post<SearchResponse>(`/api/v1/nlp/index/search/${projectUuid}`, data),

  answer: (projectUuid: string, data: SearchRequest) =>
    api.post<AnswerResponse>(`/api/v1/nlp/index/answer/${projectUuid}`, data),

  getHistory: (page = 1, pageSize = 20) =>
    api.get<QueryLogResponse>('/api/v1/nlp/history', { params: { page, page_size: pageSize } }),
}

export async function streamAnswer(
  projectUuid: string,
  data: SearchRequest,
  onChunk: (chunk: string) => void
): Promise<void> {
  const token = localStorage.getItem('kayan_access_token')
  const response = await fetch(
    `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/v1/nlp/index/answer/${projectUuid}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...data, stream: true }),
    }
  )

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || 'Stream request failed')
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const payload = line.slice(6).trim()
        if (!payload || payload === '[DONE]') return
        try {
          const parsed = JSON.parse(payload)
          const chunkText = parsed.token ?? parsed.content ?? parsed.text ?? parsed.error
          if (chunkText !== undefined) {
            onChunk(String(chunkText))
          }
        } catch {
          onChunk(payload)
        }
      }
    }
  }
}
