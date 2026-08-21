export interface AdminUser {
  user_id: string
  email: string
  full_name: string | null
  role: string
  plan: string
  monthly_llm_budget: number
  is_active: boolean
  created_at: string
}

export interface AdminUserListResponse {
  users: AdminUser[]
  page: number
  total_pages: number
}

export interface AdminUpdateUserRequest {
  role?: string
  plan?: string
  monthly_llm_budget?: number
  is_active?: boolean
}

export interface AdminQueryLog {
  log_id: string
  user_id: string
  project_id: number
  endpoint: string
  query_text: string
  result_summary: Record<string, unknown>
  status: string
  latency_ms: number
  ip_address: string | null
  request_id: string | null
  created_at: string
}

export interface AdminQueryLogResponse {
  logs: AdminQueryLog[]
  page: number
  total_pages: number
}
