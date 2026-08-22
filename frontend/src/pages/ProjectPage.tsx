import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  useDocuments,
  useUploadDocument,
  useDeleteDocument,
  useReprocessDocument,
  useProcessAndPush,
  useTaskStatus,
} from '@/hooks/useDocuments'
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
  Play,
  CheckCircle2,
  Cpu,
  Layers,
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

/* ---------- Task Status Banner Component ---------- */
function TaskBanner({ taskId, title }: { taskId: string; title: string }) {
  const { data: task, isLoading } = useTaskStatus(taskId)

  if (isLoading || !task) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-line-200 bg-paper-100 p-3 text-xs text-ink-600">
        <Spinner size="sm" />
        <span>Checking task status...</span>
      </div>
    )
  }

  const isSuccess = task.status === 'SUCCESS'
  const isPending = task.status === 'PENDING' || task.status === 'STARTED'
  const isFailed = task.status === 'FAILURE'

  return (
    <div
      className={`rounded-md border p-3 text-xs transition-all ${
        isSuccess
          ? 'border-accent-200 bg-accent-50 text-accent-800'
          : isFailed
          ? 'border-error-200 bg-error-50 text-error-800'
          : 'border-line-200 bg-paper-100 text-ink-700'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isPending && <Spinner size="sm" />}
          {isSuccess && <CheckCircle2 className="h-4 w-4 text-accent-600" />}
          {isFailed && <AlertCircle className="h-4 w-4 text-error-600" />}
          <span className="font-semibold">{title}:</span>
          <span className="font-mono uppercase">{task.status}</span>
        </div>
        <span className="font-mono text-[10px] text-ink-400">ID: {taskId.slice(0, 8)}...</span>
      </div>
      {isPending && (
        <p className="mt-1.5 text-[11px] text-ink-500">
          Task is queued/running. If it stays PENDING, ensure Celery worker is started in terminal.
        </p>
      )}
      {isSuccess && (
        <p className="mt-1 text-[11px] text-accent-700">
          Operation completed successfully. Chunks & vectors have been updated!
        </p>
      )}
      {isFailed && (
        <p className="mt-1 text-[11px] text-error-700">
          Task failed: {task.error || JSON.stringify(task.result)}
        </p>
      )}
    </div>
  )
}

/* ---------- Documents Tab ---------- */
function DocumentsTab({ projectUuid }: { projectUuid: string }) {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useDocuments(projectUuid, page)
  const upload = useUploadDocument()
  const deleteDoc = useDeleteDocument()
  const reprocessDoc = useReprocessDocument()
  const processAndPushAll = useProcessAndPush()
  const [dragOver, setDragOver] = useState(false)
  const [autoProcess, setAutoProcess] = useState(true)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [processingAssetUuid, setProcessingAssetUuid] = useState<string | null>(null)

  const handleUploadAndProcess = async (file: File) => {
    try {
      const uploadRes = await upload.mutateAsync({ projectUuid, file })
      if (autoProcess && uploadRes.data?.asset_name) {
        const procRes = await processAndPushAll.mutateAsync({
          projectUuid,
          data: {
            file_name: uploadRes.data.asset_name,
            chunk_size: 100,
            chunk_overlap: 20,
            do_reset: false,
          },
        })
        const taskId = procRes.data?.workflow_id || procRes.data?.task_id
        if (taskId) setActiveTaskId(taskId)
      }
    } catch (e) {
      console.error('Upload failed:', e)
    }
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) await handleUploadAndProcess(file)
  }

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) await handleUploadAndProcess(file)
  }

  const handleProcessSingle = async (assetUuid: string, assetName: string) => {
    setProcessingAssetUuid(assetUuid)
    try {
      const res = await reprocessDoc.mutateAsync({
        projectUuid,
        assetUuid,
        data: {
          file_name: assetName,
          chunk_size: 100,
          chunk_overlap: 20,
          do_reset: false,
        },
      })
      const taskId = res.data?.workflow_id || res.data?.task_id
      if (taskId) setActiveTaskId(taskId)
    } finally {
      setProcessingAssetUuid(null)
    }
  }

  const handleProcessAll = async () => {
    const res = await processAndPushAll.mutateAsync({
      projectUuid,
      data: {
        chunk_size: 100,
        chunk_overlap: 20,
        do_reset: false,
      },
    })
    const taskId = res.data?.workflow_id || res.data?.task_id
    if (taskId) setActiveTaskId(taskId)
  }

  return (
    <div className="space-y-6">
      {/* Upload Box */}
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
        <div className="mt-3 flex items-center justify-center gap-2 text-xs text-ink-500">
          <input
            type="checkbox"
            id="autoProcess"
            checked={autoProcess}
            onChange={(e) => setAutoProcess(e.target.checked)}
            className="rounded border-line-300 text-accent-600 focus:ring-accent-500"
          />
          <label htmlFor="autoProcess" className="cursor-pointer font-sans select-none">
            Auto-chunk & index into VectorDB immediately after upload
          </label>
        </div>
        {(upload.isPending || processAndPushAll.isPending) && <Spinner className="mt-4" />}
      </div>

      {/* Task Status Banner */}
      {activeTaskId && <TaskBanner taskId={activeTaskId} title="Background Task" />}

      {/* Action Header */}
      {data?.documents && data.documents.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-paper-50 p-3 border border-line-200">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-ink-500" />
            <span className="text-xs font-semibold text-ink-800">
              {data.total_documents} {data.total_documents === 1 ? 'Document' : 'Documents'} Total
            </span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleProcessAll}
            isLoading={processAndPushAll.isPending}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Process & Index All Documents
          </Button>
        </div>
      )}

      {/* Document List */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : !data?.documents.length ? (
        <EmptyState icon={FileText} title="No documents" description="Upload files to build your corpus." />
      ) : (
        <div className="space-y-3">
          {data.documents.map((doc) => {
            const isProcessingThis = processingAssetUuid === doc.asset_uuid
            const hasChunks = (doc.total_chunks ?? 0) > 0

            return (
              <Card key={doc.asset_uuid} padding="md">
                <CardContent>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-start sm:items-center gap-3">
                      <FileText className="h-5 w-5 text-ink-400 stroke-[1.5] mt-0.5 sm:mt-0 shrink-0" />
                      <div>
                        <p className="text-sm font-sans font-medium text-ink-900 break-all">{doc.asset_name}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs font-mono text-ink-400">
                          <span>{formatBytes(doc.asset_size)}</span>
                          <span>·</span>
                          <span>v{doc.asset_version}</span>
                          <span>·</span>
                          <span>{formatDate(doc.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                      <Badge variant={hasChunks ? 'success' : 'default'}>
                        <Layers className="mr-1 h-3 w-3 inline" />
                        {doc.total_chunks ?? 0} {doc.total_chunks === 1 ? 'chunk' : 'chunks'}
                      </Badge>

                      <Badge variant={doc.is_latest ? 'accent' : 'default'}>
                        {doc.is_latest ? 'Latest' : 'Archived'}
                      </Badge>

                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleProcessSingle(doc.asset_uuid, doc.asset_name)}
                        isLoading={isProcessingThis}
                        title="Chunk file and push into VectorDB"
                      >
                        <Play className="mr-1 h-3 w-3" />
                        {hasChunks ? 'Reprocess' : 'Process & Push'}
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteDoc.mutateAsync({ projectUuid, assetUuid: doc.asset_uuid })}
                        isLoading={deleteDoc.isPending}
                        className="text-ink-400 hover:text-error-600"
                        title="Delete document and purge vectors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
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
  const { data: info, isLoading, refetch } = useIndexInfo(projectUuid)
  const pushIndex = usePushIndex(projectUuid)
  const processAndPushAll = useProcessAndPush()
  const [indexTaskId, setIndexTaskId] = useState<string | null>(null)

  const handlePushIndex = async () => {
    try {
      const res = await pushIndex.mutateAsync({ do_reset: false })
      if (res.data?.task_id) {
        setIndexTaskId(res.data.task_id)
      }
    } catch (e) {
      console.error('Push index failed:', e)
    }
  }

  const handleProcessAndPushAll = async () => {
    try {
      const res = await processAndPushAll.mutateAsync({
        projectUuid,
        data: { chunk_size: 100, chunk_overlap: 20, do_reset: false },
      })
      const taskId = res.data?.workflow_id || res.data?.task_id
      if (taskId) setIndexTaskId(taskId)
    } catch (e) {
      console.error('Process and push all failed:', e)
    }
  }

  return (
    <div className="space-y-6">
      {indexTaskId && <TaskBanner taskId={indexTaskId} title="Vector Indexing Task" />}

      <Card padding="lg">
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-h3 font-sans font-semibold text-ink-900">Vector Index Management</h3>
              <p className="mt-1 text-sm text-ink-400">
                Generate embeddings and synchronize chunks with the Qdrant vector database.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={handleProcessAndPushAll}
                isLoading={processAndPushAll.isPending}
                title="Parse documents, generate chunks, and push all to vector DB"
              >
                <Cpu className="mr-1.5 h-4 w-4" />
                Process & Index All
              </Button>
              <Button
                variant="primary"
                onClick={handlePushIndex}
                isLoading={pushIndex.isPending}
                title="Index existing database chunks into vector DB"
              >
                <RefreshCw className="mr-1.5 h-4 w-4" />
                Push Index (Existing Chunks)
              </Button>
            </div>
          </div>

          <div className="rounded-md border border-line-200 bg-paper-50 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-500 font-mono">
                Collection Status & Metadata
              </span>
              <Button variant="ghost" size="sm" onClick={() => refetch()} className="text-xs text-ink-400">
                <RefreshCw className="mr-1 h-3 w-3" /> Refresh
              </Button>
            </div>

            {isLoading ? (
              <Spinner />
            ) : info?.collection_info ? (
              <pre className="rounded-sm border border-line-200 bg-paper-0 p-4 text-mono font-mono text-xs text-ink-700 overflow-auto max-h-96">
                {JSON.stringify(info.collection_info, null, 2)}
              </pre>
            ) : (
              <div className="text-sm text-ink-400 py-4 text-center">
                <AlertCircle className="mx-auto h-5 w-5 text-ink-400 mb-1" />
                No vector index found for this project yet. Use <b>"Process & Index All"</b> to initialize.
              </div>
            )}
          </div>
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
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: userMsg },
      { role: 'assistant', text: '' },
    ])
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
            if (last && last.role === 'assistant') {
              last.text = assistantText
            }
            return next
          })
        },
      })
    } catch (err: any) {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last && last.role === 'assistant') {
          last.text = last.text || (err?.message || 'An error occurred. Please verify your LLM API configuration.')
        }
        return next
      })
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-280px)] flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto pr-2">
        {!messages.length && (
          <EmptyState
            icon={MessageSquare}
            title="Ask anything about your project"
            description="Responses are grounded in the documents indexed in your knowledge base."
          />
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[80%] rounded-sm border border-line-200 bg-paper-100 px-4 py-3">
                <p className="text-sm font-sans text-ink-900">{msg.text}</p>
              </div>
            ) : (
              <div className="max-w-[80%] border-l-2 border-accent-600 pl-4 py-1">
                {msg.text ? (
                  <p className="text-sm font-sans text-ink-900 leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                ) : streaming ? (
                  <div className="flex items-center gap-2.5 py-1.5 text-xs text-ink-500">
                    <span className="font-sans font-medium text-accent-700 tracking-wide">Processing query</span>
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-paper-100 rounded-full border border-line-200 shadow-sm">
                      <span className="h-1.5 w-1.5 rounded-full bg-accent-600 animate-dot-1" />
                      <span className="h-1.5 w-1.5 rounded-full bg-accent-600 animate-dot-2" />
                      <span className="h-1.5 w-1.5 rounded-full bg-accent-600 animate-dot-3" />
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        ))}
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
