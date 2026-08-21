import { useState } from 'react'
import { useQueryHistory } from '@/hooks/useNlp'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/Card'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { formatDate } from '@/lib/utils'
import { History, Clock } from 'lucide-react'

export const HistoryPage = () => {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQueryHistory(page)

  return (
    <div className="space-y-8">
      <Header title="Query History" subtitle="Your search and answer activity" />
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : !data?.logs.length ? (
        <EmptyState icon={History} title="No history yet" description="Your queries will appear here." />
      ) : (
        <div className="space-y-3">
          {data.logs.map((log) => (
            <Card key={log.log_id} padding="md">
              <CardContent>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <p className="text-sm font-sans font-medium text-ink-900">{log.query_text}</p>
                    <div className="mt-1.5 flex items-center gap-3 text-xs font-mono text-ink-400">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDate(log.created_at)}
                      </span>
                      <span>·</span>
                      <span>{log.endpoint}</span>
                      <span>·</span>
                      <span>{log.latency_ms}ms</span>
                      <span>·</span>
                      <span className={`${
                        log.status === 'success' ? 'text-success-600' :
                        log.status === 'error' ? 'text-error-600' : 'text-warning-600'
                      }`}>{log.status}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          {data.total_pages > 1 && (
            <Pagination page={page} totalPages={data.total_pages} onPageChange={setPage} />
          )}
        </div>
      )}
    </div>
  )
}
