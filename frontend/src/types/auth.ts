export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface RefreshRequest {
  token: string
}

export interface LogoutRequest {
  token?: string
}

export interface UserProfile {
  user_id: string
  email: string
  full_name: string | null
  role: 'admin' | 'member' | 'viewer'
  plan: string
  monthly_llm_budget: number
  is_active: boolean
  created_at: string
}

export interface UpdateProfileRequest {
  full_name?: string
}

export interface ApiKey {
  key_id: string
  name: string | null
  api_key?: string
  created_at: string
}

export interface CreateApiKeyRequest {
  name?: string
}
