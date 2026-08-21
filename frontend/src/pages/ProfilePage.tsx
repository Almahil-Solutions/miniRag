import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/users'
import { Header } from '@/components/layout/Header'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { formatDate } from '@/lib/utils'
import { KeyRound, Copy, CheckCircle2 } from 'lucide-react'

export const ProfilePage = () => {
  const { user, setUser } = useAuthStore()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [updating, setUpdating] = useState(false)
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleUpdate = async () => {
    setUpdating(true)
    try {
      const { data } = await usersApi.updateMe({ full_name: fullName })
      setUser(data)
    } finally {
      setUpdating(false)
    }
  }

  const handleCreateKey = async () => {
    const { data } = await usersApi.createApiKey({ name: 'Default' })
    if (data.api_key) setApiKey(data.api_key)
  }

  const copyKey = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (!user) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>

  return (
    <div className="space-y-8">
      <Header title="Profile" subtitle="Manage your account" />
      <div className="grid gap-6 md:grid-cols-2">
        <Card padding="lg">
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-sans font-medium uppercase tracking-wider text-ink-400">Email</label>
              <p className="text-sm font-sans text-ink-900">{user.email}</p>
            </div>
            <Input
              label="Full name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <Badge variant="accent">{user.role}</Badge>
              <Badge variant="default">{user.plan}</Badge>
            </div>
            <Button variant="primary" onClick={handleUpdate} isLoading={updating}>
              Save changes
            </Button>
          </CardContent>
        </Card>

        <Card padding="lg">
          <CardHeader>
            <CardTitle>API Keys</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-ink-400">
              Generate API keys for programmatic access. Keys are shown once.
            </p>
            {apiKey ? (
              <div className="rounded-sm border border-accent-600/20 bg-accent-100/30 p-3">
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-mono font-mono text-ink-900 break-all">{apiKey}</code>
                  <Button variant="ghost" size="sm" onClick={copyKey}>
                    {copied ? <CheckCircle2 className="h-4 w-4 text-success-600" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="mt-2 text-xs text-accent-700">Copy this now. It will not be shown again.</p>
              </div>
            ) : (
              <Button variant="secondary" onClick={handleCreateKey}>
                <KeyRound className="mr-1.5 h-4 w-4" />
                Generate key
              </Button>
            )}
          </CardContent>
        </Card>

        <Card padding="lg">
          <CardHeader>
            <CardTitle>Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-ink-400">Monthly LLM budget</span>
              <span className="font-mono text-ink-900">${user.monthly_llm_budget.toFixed(2)}</span>
            </div>
            <div className="h-2 w-full rounded-sm bg-line-200 overflow-hidden">
              <div className="h-full bg-accent-600" style={{ width: '0%' }} />
            </div>
            <p className="text-xs text-ink-400">Budget resets monthly.</p>
          </CardContent>
        </Card>

        <Card padding="lg">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-ink-400">User ID</span>
              <span className="font-mono text-ink-700">{user.user_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-400">Status</span>
              <span className={user.is_active ? 'text-success-600' : 'text-error-600'}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-400">Created</span>
              <span className="font-mono text-ink-700">{formatDate(user.created_at)}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
