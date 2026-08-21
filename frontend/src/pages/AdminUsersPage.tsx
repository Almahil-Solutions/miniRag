import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminUsers } from '@/hooks/useAdmin'
import { Header } from '@/components/layout/Header'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { formatDate } from '@/lib/utils'
import { Users, FileText } from 'lucide-react'

export const AdminUsersPage = () => {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useAdminUsers(page)

  return (
    <div className="space-y-8">
      <Header title="Administration" subtitle="User management">
        <div className="flex gap-2">
          <Link to="/admin/users">
            <Button variant="secondary" size="sm" className="gap-1.5">
              <Users className="h-4 w-4" /> Users
            </Button>
          </Link>
          <Link to="/admin/logs">
            <Button variant="ghost" size="sm" className="gap-1.5">
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
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Budget</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.users.map((u) => (
                <TableRow key={u.user_id}>
                  <TableCell>
                    <div>
                      <p className="font-medium text-ink-900">{u.full_name || u.email}</p>
                      <p className="text-xs font-mono text-ink-400">{u.email}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={u.role === 'admin' ? 'accent' : 'default'}>{u.role}</Badge>
                  </TableCell>
                  <TableCell>{u.plan}</TableCell>
                  <TableCell className="font-mono">${u.monthly_llm_budget.toFixed(2)}</TableCell>
                  <TableCell>
                    <span className={u.is_active ? 'text-success-600' : 'text-error-600'}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-ink-400">{formatDate(u.created_at)}</TableCell>
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
