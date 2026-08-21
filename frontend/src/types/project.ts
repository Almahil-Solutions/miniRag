export interface Project {
  project_id: number
  project_uuid: string
}

export interface ProjectListResponse {
  projects: Project[]
  total_pages: number
  page: number
}
