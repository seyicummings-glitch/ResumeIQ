import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { FolderOpen, Download, Trash2, Check, X } from 'lucide-react'
import { useDocuments, useDeleteDocument, useDownloadDocument } from '../hooks/useDocuments'
import { Table, TableHead, Th, TableBody, Td } from '../components/ui/Table'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import { buttonClasses } from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import { useToast } from '../components/ui/Toast'

const DOC_TYPE_LABELS = {
  'analysis-report': 'Analysis report',
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

function formatSize(sizeKb) {
  if (sizeKb === null || sizeKb === undefined) return '—'
  if (sizeKb >= 1024) return `${(sizeKb / 1024).toFixed(1)} MB`
  return `${sizeKb} KB`
}

function isSameMonth(dateValue, reference) {
  const date = new Date(dateValue)
  return date.getFullYear() === reference.getFullYear() && date.getMonth() === reference.getMonth()
}

function DocumentRow({ document, onDeleted }) {
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const downloadMutation = useDownloadDocument()
  const deleteMutation = useDeleteDocument()
  const { showToast } = useToast()

  async function handleDownload() {
    try {
      await downloadMutation.mutateAsync(document.id)
    } catch (error) {
      showToast(error.message, { tone: 'error' })
    }
  }

  async function handleConfirmDelete() {
    try {
      await deleteMutation.mutateAsync(document.id)
      showToast('Document deleted.', { tone: 'success' })
      onDeleted?.()
    } catch (error) {
      showToast(error.message, { tone: 'error' })
    } finally {
      setConfirmingDelete(false)
    }
  }

  return (
    <tr>
      <Td className="font-medium text-text-h">{document.name}</Td>
      <Td>
        <Badge tone="accent">{DOC_TYPE_LABELS[document.doc_type] || document.doc_type}</Badge>
      </Td>
      <Td>{formatDate(document.created_at)}</Td>
      <Td>{formatSize(document.size_kb)}</Td>
      <Td>
        {confirmingDelete ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text">Delete?</span>
            <button
              type="button"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              aria-label={`Confirm delete ${document.name}`}
              className="inline-flex items-center justify-center rounded-md p-1.5 text-danger hover:bg-danger-bg disabled:opacity-50"
            >
              <Check size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(false)}
              disabled={deleteMutation.isPending}
              aria-label="Cancel delete"
              className="inline-flex items-center justify-center rounded-md p-1.5 text-text hover:bg-surface disabled:opacity-50"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDownload}
              disabled={downloadMutation.isPending}
              aria-label={`Download ${document.name}`}
              className="inline-flex items-center justify-center rounded-md p-1.5 text-accent hover:bg-accent/10 disabled:opacity-50"
            >
              <Download size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              aria-label={`Delete ${document.name}`}
              className="inline-flex items-center justify-center rounded-md p-1.5 text-danger hover:bg-danger-bg"
            >
              <Trash2 size={16} aria-hidden="true" />
            </button>
          </div>
        )}
      </Td>
    </tr>
  )
}

export default function DocumentsPage() {
  const { data, isLoading, isError, error, refetch } = useDocuments()

  const stats = useMemo(() => {
    if (!data) return { total: 0, thisMonth: 0, totalStorageKb: 0 }
    const now = new Date()
    return {
      total: data.length,
      thisMonth: data.filter((doc) => isSameMonth(doc.created_at, now)).length,
      totalStorageKb: data.reduce((sum, doc) => sum + (doc.size_kb || 0), 0),
    }
  }, [data])

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading documents…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Documents</h1>
        <p className="mt-1 text-sm text-text">PDF reports generated from your saved analyses.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-text">Total documents</p>
          <p className="mt-1 text-2xl font-semibold text-text-h">{stats.total}</p>
        </Card>
        <Card>
          <p className="text-sm text-text">Generated this month</p>
          <p className="mt-1 text-2xl font-semibold text-text-h">{stats.thisMonth}</p>
        </Card>
        <Card>
          <p className="text-sm text-text">Total storage</p>
          <p className="mt-1 text-2xl font-semibold text-text-h">{formatSize(stats.totalStorageKb)}</p>
        </Card>
      </div>

      {data.length === 0 ? (
        <EmptyState
          icon={FolderOpen}
          title="No documents yet"
          description="Documents are PDF reports generated from a saved analysis. Run an analysis on your dashboard or open one from your history, then generate a report."
          action={
            <div className="flex gap-2">
              <Link to="/dashboard" className={buttonClasses()}>
                Go to dashboard
              </Link>
              <Link to="/history" className={buttonClasses({ variant: 'secondary' })}>
                View history
              </Link>
            </div>
          }
        />
      ) : (
        <Table>
          <TableHead>
            <Th>Name</Th>
            <Th>Type</Th>
            <Th>Created</Th>
            <Th>Size</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </TableHead>
          <TableBody>
            {data.map((document) => (
              <DocumentRow key={document.id} document={document} onDeleted={refetch} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
