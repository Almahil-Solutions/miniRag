import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useDocuments, useUploadDocument, useDeleteDocument } from '@/hooks/useDocuments'
import { useIndexInfo, usePushIndex, useSearch, useStreamAnswer } from '@/hooks/useNlp'
import { Header } from '@/components/layout/Header'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Badge } from '@/components/ui/Badge'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { formatBytes, formatDate, truncate } from '@/lib/utils'
import {
  FileUp,
  Trash2,
  Search,
  MessageSquare,
  Database,
  FileText,
  AlertCircle,
  RefreshCw,
  Send,
} from 'lucide-react'

type Tab = 'documents' | 'index' | 'search' | 'chat'

export const ProjectPage = () => {
  const { projectUuid } = useParams<{ projectUuid: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') as Tab) || 'documents'
  const setTab = (t: Tab) => setSearchParams({ tab: t })

  if (!projectUuid) return null

  return (
    <div className="space-y-8">
      <Header title="Project" subtitle={projectUuid} />
      <div className="border-b border-line-200">
        <nav className="flex gap-1">
          {([
            { id: 'documents' as Tab, label: 'Documents', icon: FileText },
            { id: 'index' as Tab, label: 'Index', icon: Database },
            { id: 'search' as Tab, label: 'Search', icon: Search },
            { id: 'chat' as Tab, label: 'Chat', icon: MessageSquare },
          ]).map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`flex items-center gap-2 rounded-t-sm px-4 py-2.5 text-sm font-sans font-medium transition-colors ${
                tab === item.id
                  ? 'border-b-2 border-accent-600 text-accent-700'
                  : 'text-ink-400 hover:text-ink-700'
              }`}
            >
              <item.icon className="h-4 w-4 stroke-[1.5]" />
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'documents' && <DocumentsTab projectUuid={projectUuid} />}
      {tab === 'index' && <IndexTab projectUuid={projectUuid} />}
      {tab === 'search' && <SearchTab projectUuid={projectUuid} />}
      {tab === 'chat' && <ChatTab projectUuid={projectUuid} />}
    </div>
  )
}

/* ---------- Documents Tab ---------- */
function DocumentsTab({ projectUuid }: { projectUuid: string }) {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useDocuments(projectUuid, page)
  const upload = useUploadDocument()
  const deleteDoc = useDeleteDocument()
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) await upload.mutateAsync({ projectUuid, file })
  }

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) await upload.mutateAsync({ projectUuid, file })
  }

  return (
    <div className="space-y-6">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`rounded-md border-2 border-dashed p-8 text-center transition-colors ${
          dragOver ? 'border-accent-600 bg-accent-100/30' : 'border-line-200'
        }`}
      >
        <FileUp className="mx-auto h-6 w-6 text-ink-400 stroke-[1.5]" />
        <p className="mt-3 text-sm font-sans font-medium text-ink-700">
          Drop a file here, or{' '}
          <label className="cursor-pointer text-accent-700 hover:underline">
            browse
            <input type="file" className="hidden" onChange={handleFileInput} />
          </label>
        </p>
        <p className="mt-1 text-xs text-ink-400">Supported formats: PDF, TXT, DOCX</p>
        {upload.isPending && <Spinner className="mt-4" />}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : !data?.documents.length ? (
        <EmptyState icon={FileText} title="No documents" description="Upload files to build your corpus." />
      ) : (
        <div className="space-y-3">
          {data.documents.map((doc) => (
            <Card key={doc.asset_uuid} padding="md">
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-ink-400 stroke-[1.5]" />
                    <div>
                      <p className="text-sm font-sans font-medium text-ink-900">{doc.asset_name}</p>
                      <div className="mt-1 flex items-center gap-2 text-xs font-mono text-ink-400">
                        <span>{formatBytes(doc.asset_size)}</span>
                        <span>·</span>
                        <span>v{doc.asset_version}</span>
                        <span>·</span>
                        <span>{formatDate(doc.created_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={doc.is_latest ? 'success' : 'default'}>
                      {doc.is_latest ? 'Latest' : 'Archived'}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteDoc.mutateAsync({ projectUuid, assetUuid: doc.asset_uuid })}
                      isLoading={deleteDoc.isPending}
                      className="text-ink-400 hover:text-error-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
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

/* ---------- Index Tab ---------- */
function IndexTab({ projectUuid }: { projectUuid: string }) {
  const { data: info, isLoading } = useIndexInfo(projectUuid)
  const pushIndex = usePushIndex(projectUuid)

  return (
    <div className="space-y-6">
      <Card padding="lg">
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-h3 font-sans font-semibold text-ink-900">Vector Index</h3>
              <p className="mt-1 text-sm text-ink-400">Manage your project's semantic index.</p>
            </div>
            <Button
              variant="primary"
              onClick={() => pushIndex.mutateAsync({ do_reset: false })}
              isLoading={pushIndex.isPending}
            >
              <RefreshCw className="mr-1.5 h-4 w-4" />
              Push Index
            </Button>
          </div>

          {isLoading ? (
            <Spinner />
          ) : info ? (
            <pre className="rounded-sm border border-line-200 bg-paper-0 p-4 text-mono font-mono text-ink-700 overflow-auto">
              {JSON.stringify(info.collection_info, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-ink-400">No index information available.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

/* ---------- Search Tab ---------- */
function SearchTab({ projectUuid }: { projectUuid: string }) {
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(5)
  const search = useSearch(projectUuid)
  const [results, setResults] = useState<null | Awaited<ReturnType<typeof search.mutateAsync>>>(null)

  const handleSearch = async () => {
    if (!query.trim()) return
    const res = await search.mutateAsync({ text: query, limit })
    setResults(res)
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-3">
        <Input
          placeholder="Search your documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="flex-1"
        />
        <Input
          type="number"
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="w-20"
        />
        <Button variant="primary" onClick={handleSearch} isLoading={search.isPending}>
          <Search className="mr-1.5 h-4 w-4" />
          Search
        </Button>
      </div>

      {search.isError && (
        <div className="flex items-center gap-2 rounded-sm border border-error-600/20 bg-error-600/5 px-3 py-2 text-sm text-error-600">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Search failed. Please try again.
        </div>
      )}

      {results?.data.results.length ? (
        <div className="space-y-3">
          {results.data.results.map((result, i) => (
            <Card key={i} padding="md">
              <CardContent>
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 text-xs font-mono text-accent-700">[{i + 1}]</span>
                  <div className="flex-1">
                    <p className="text-sm font-mono text-ink-700 leading-relaxed">{truncate(result.text, 400)}</p>
                    <p className="mt-2 text-xs font-mono text-ink-400">Score: {result.score.toFixed(4)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : results ? (
        <EmptyState icon={Search} title="No matches found" description="Try a different query." />
      ) : null}
    </div>
  )
}

/* ---------- Chat Tab ---------- */
function ChatTab({ projectUuid }: { projectUuid: string }) {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([])
  const [streaming, setStreaming] = useState(false)
  const streamAnswer = useStreamAnswer()

  const handleSend = async () => {
    if (!query.trim() || streaming) return
    const userMsg = query.trim()
    setQuery('')
    setMessages((prev) => [...prev, { role: 'user', text: userMsg }])
    setStreaming(true)

    let assistantText = ''
    try {
      await streamAnswer.mutateAsync({
        projectUuid,
        data: { text: userMsg, limit: 5 },
        onChunk: (chunk) => {
          assistantText += chunk
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last?.role === 'assistant') {
              last.text = assistantText
            } else {
              next.push({ role: 'assistant', text: assistantText })
            }
            return next
          })
        },
      })
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', text: 'An error occurred. Please try again.' }])
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-280px)] flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto pr-2">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[80%] rounded-sm border border-line-200 bg-paper-100 px-4 py-3">
                <p className="text-sm font-sans text-ink-900">{msg.text}</p>
              </div>
            ) : (
              <div className="max-w-[80%] border-l-2 border-accent-600 pl-4">
                <p className="text-sm font-sans text-ink-900 leading-relaxed whitespace-pre-wrap">{msg.text}</p>
              </div>
            )}
          </div>
        ))}
        {streaming && messages[messages.length - 1]?.role === 'assistant' && messages[messages.length - 1].text === '' && (
          <div className="flex justify-start">
            <div className="border-l-2 border-accent-600 pl-4">
              <Spinner size="sm" />
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex gap-3 border-t border-line-200 pt-4">
        <Textarea
          placeholder="Ask a question..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }}}
          className="min-h-[48px] flex-1 resize-none"
          rows={1}
        />
        <Button variant="primary" onClick={handleSend} isLoading={streaming} className="self-end">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
