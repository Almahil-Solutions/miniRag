import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminQueryLogs } from '@/hooks/useAdmin'
import { Header } from '@/components/layout/Header'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { formatDate } from '@/lib/utils'
import { Users, FileText } from 'lucide-react'

export const AdminLogsPage = () => {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useAdminQueryLogs(page)

  return (
    <div className="space-y-8">
      <Header title="Administration" subtitle="Query logs">
        <div className="flex gap-2">
          <Link to="/admin/users">
            <Button variant="ghost" size="sm" className="gap-1.5">
              <Users className="h-4 w-4" /> Users
            </Button>
          </Link>
          <Link to="/admin/logs">
            <Button variant="secondary" size="sm" className="gap-1.5">
              <FileText className="h-4 w-4" /> Logs
            </Button>
          </Link>
        </div>
      </Header>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <div className="rounded-md border border-line-200 bg-paper-100">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Endpoint</TableHead>
                <TableHead>Query</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Latency</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.logs.map((log) => (
                <TableRow key={log.log_id}>
                  <TableCell className="font-mono text-xs text-ink-400 whitespace-nowrap">
                    {formatDate(log.created_at)}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-ink-400">{log.user_id.slice(0, 8)}...</TableCell>
                  <TableCell className="text-xs">{log.endpoint}</TableCell>
                  <TableCell className="max-w-xs truncate text-xs" title={log.query_text}>
                    {log.query_text}
                  </TableCell>
                  <TableCell>
                    <Badge variant={
                      log.status === 'success' ? 'success' :
                      log.status === 'error' ? 'error' : 'warning'
                    }>{log.status}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{log.latency_ms}ms</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {data && data.total_pages > 1 && (
            <div className="flex justify-center border-t border-line-200 p-4">
              <Pagination page={page} totalPages={data.total_pages} onPageChange={setPage} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
