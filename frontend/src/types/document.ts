export interface ProcessRequest {
  file_name?: string
  chunk_size?: number
  chunk_overlap?: number
  do_reset?: boolean
}

export interface DocumentAsset {
  asset_id: number
  asset_uuid: string
  asset_name: string
  asset_type: string
  asset_size: number
  asset_version: number
  is_latest: boolean
  total_chunks?: number
  asset_config: Record<string, unknown>
  created_at: string
}

export interface DocumentListResponse {
  documents: DocumentAsset[]
  total_documents: number
  total_pages: number
  page: number
}

export interface DocumentDetailResponse {
  asset_id: number
  asset_uuid: string
  asset_name: string
  asset_type: string
  asset_size: number
  asset_version: number
  is_latest: boolean
  total_chunks: number
  asset_config: Record<string, unknown>
  created_at: string
  available_versions: number[]
}

export interface UploadResponse {
  result_signal: string
  asset_name: string
  asset_id: string
  asset_uuid: string
  asset_version: number
  is_latest: boolean
}

export interface TaskResponse {
  result_signal: string
  task_id?: string
  workflow_id?: string
}

export interface TaskStatusResponse {
  task_id: string
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'UNKNOWN'
  ready: boolean
  successful?: boolean
  result?: unknown
  error?: string
}

