import { api } from './client'
import type { Project, ProjectListResponse } from '@/types'

export const projectsApi = {
  create: () => api.post<Project>('/api/v1/projects'),

  list: (page = 1, pageSize = 10) =>
    api.get<ProjectListResponse>('/api/v1/projects', { params: { page, page_size: pageSize } }),

  delete: (projectUuid: string) =>
    api.delete(`/api/v1/projects/${projectUuid}`),
}
