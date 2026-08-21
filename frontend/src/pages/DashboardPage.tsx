import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, FolderOpen, Trash2, AlertCircle } from 'lucide-react'
import { useProjects, useCreateProject, useDeleteProject } from '@/hooks/useProjects'
import { Header } from '@/components/layout/Header'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { formatDate } from '@/lib/utils'

export const DashboardPage = () => {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useProjects(page)
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleCreate = async () => {
    await createProject.mutateAsync()
  }

  const handleDelete = async (projectUuid: string) => {
    setDeletingId(projectUuid)
    await deleteProject.mutateAsync(projectUuid)
    setDeletingId(null)
  }

  return (
    <div className="space-y-8">
      <Header
        title="Projects"
        subtitle="Your knowledge corpora"
      >
        <Button
          variant="primary"
          size="md"
          onClick={handleCreate}
          isLoading={createProject.isPending}
        >
          <Plus className="mr-1.5 h-4 w-4" />
          New project
        </Button>
      </Header>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      ) : !data?.projects.length ? (
        <EmptyState
          icon={FolderOpen}
          title="No projects yet"
          description="Create a project to start indexing your documents."
        />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3">
            {data.projects.map((project) => (
              <Card key={project.project_uuid} padding="md">
                <CardContent>
                  <div className="flex items-center justify-between">
                    <Link
                      to={`/projects/${project.project_uuid}`}
                      className="flex-1 group"
                    >
                      <div className="flex items-center gap-3">
                        <FolderOpen className="h-5 w-5 text-ink-400 group-hover:text-accent-600 transition-colors stroke-[1.5]" />
                        <div>
                          <p className="text-sm font-sans font-medium text-ink-900 group-hover:text-accent-700 transition-colors">
                            Project {project.project_id}
                          </p>
                          <p className="text-xs font-mono text-ink-400 mt-0.5">
                            {project.project_uuid}
                          </p>
                        </div>
                      </div>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(project.project_uuid)}
                      isLoading={deletingId === project.project_uuid}
                      className="text-ink-400 hover:text-error-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {data.total_pages > 1 && (
            <div className="flex justify-center pt-4">
              <Pagination
                page={page}
                totalPages={data.total_pages}
                onPageChange={setPage}
              />
            </div>
          )}
        </div>
      )}

      {createProject.isError ? (
        <div className="flex items-center gap-2 rounded-sm border border-error-600/20 bg-error-600/5 px-3 py-2 text-sm text-error-600">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to create project. Please try again.
        </div>
      ) : null}
    </div>
  )
}
