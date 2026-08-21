export interface PushRequest {
  do_reset?: boolean
}

export interface SearchRequest {
  text: string
  limit?: number
  language?: string
  stream?: boolean
}

export interface SearchResult {
  score: number
  text: string
  metadata: Record<string, unknown>
}

export interface SearchResponse {
  signal: string
  results: SearchResult[]
}

export interface AnswerResponse {
  signal: string
  answer: string
  full_prompt?: string
  chat_history?: unknown[]
}

export interface IndexInfoResponse {
  signal: string
  collection_info: Record<string, unknown>
}

export interface QueryLog {
  log_id: string
  project_id: number
  endpoint: string
  query_text: string
  result_summary: Record<string, unknown>
  status: string
  latency_ms: number
  created_at: string
}

export interface QueryLogResponse {
  logs: QueryLog[]
  page: number
  total_pages: number
}
