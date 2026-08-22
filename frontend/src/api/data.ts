import { api } from './client'
import type {
  DocumentListResponse,
  DocumentDetailResponse,
  UploadResponse,
  ProcessRequest,
  TaskResponse,
  TaskStatusResponse,
} from '@/types'

export const dataApi = {
  upload: (projectUuid: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<UploadResponse>(`/api/v1/data/upload/${projectUuid}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  listDocuments: (projectUuid: string, page = 1, pageSize = 10, assetType?: string) =>
    api.get<DocumentListResponse>(`/api/v1/data/${projectUuid}/documents`, {
      params: { page, page_size: pageSize, asset_type: assetType, only_latest: true },
    }),

  getDocument: (projectUuid: string, assetUuid: string) =>
    api.get<DocumentDetailResponse>(`/api/v1/data/${projectUuid}/documents/${assetUuid}`),

  deleteDocument: (projectUuid: string, assetUuid: string) =>
    api.delete(`/api/v1/data/${projectUuid}/documents/${assetUuid}`),

  reprocessDocument: (projectUuid: string, assetUuid: string, data: ProcessRequest) =>
    api.post<TaskResponse>(`/api/v1/data/${projectUuid}/documents/${assetUuid}/reprocess`, data),

  process: (projectUuid: string, data: ProcessRequest) =>
    api.post<TaskResponse>(`/api/v1/data/process/${projectUuid}`, data),

  processAndPush: (projectUuid: string, data: ProcessRequest) =>
    api.post<TaskResponse>(`/api/v1/data/process-and-push/${projectUuid}`, data),

  getTaskStatus: (taskId: string) =>
    api.get<TaskStatusResponse>(`/api/v1/data/task/${taskId}`),
}

