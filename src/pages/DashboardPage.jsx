import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, ArrowRight, FileText, Download, Trash2, RefreshCw, Eye, Check, X, ChevronsUpDown, Search } from 'lucide-react'
import { useAnalysisHistory } from '../hooks/useAnalysisHistory'
import { useProfile } from '../hooks/useProfile'
import { useResumeVersions, useDeleteResume, useBulkDeleteResumes, useDownloadResume } from '../hooks/useResumeVersions'
import * as matchingApi from '../api/matching'
import Card from '../components/ui/Card'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import ScoreBadge from '../components/ui/ScoreBadge'
import Badge from '../components/ui/Badge'
import Button, { buttonClasses } from '../components/ui/Button'
import Input from '../components/ui/Input'
import { Table, TableHead, Th, TableBody, Td } from '../components/ui/Table'
import EmptyState from '../components/ui/EmptyState'
import { useToast } from '../components/ui/Toast'

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

function ResumeRow({ resume, selected, onToggleSelect }) {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  const downloadMutation = useDownloadResume()
  const deleteMutation = useDeleteResume()
  const reanalyzeMutation = useMutation({
    mutationFn: () => matchingApi.saveAnalysis({ resumeId: resume.id, jobDescriptionId: resume.latestJobDescriptionId }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['resumeVersions'] })
      queryClient.invalidateQueries({ queryKey: ['analysisHistory'] })
      showToast('Re-analyzed against the same job description.', { tone: 'success' })
      navigate(`/analysis-results/${result.analysis_id}`)
    },
    onError: (error) => showToast(error.message, { tone: 'error' }),
  })

  async function handleDownload() {
    try {
      await downloadMutation.mutateAsync({ resumeId: resume.id, filename: resume.filename })
    } catch (error) {
      showToast(error.message, { tone: 'error' })
    }
  }

  async function handleConfirmDelete() {
    try {
      await deleteMutation.mutateAsync(resume.id)
      showToast('Resume deleted.', { tone: 'success' })
    } catch (error) {
      showToast(error.message, { tone: 'error' })
    } finally {
      setConfirmingDelete(false)
    }
  }

  return (
    <tr className="group">
      <Td className="w-10 opacity-0 transition-opacity group-hover:opacity-100 has-[:checked]:opacity-100 has-[:focus-visible]:opacity-100">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggleSelect(resume.id)}
          aria-label={`Select ${resume.latestJobTitle || resume.filename}`}
          className="h-4 w-4 rounded border-border accent-accent"
        />
      </Td>
      <Td className="font-medium text-text-h">
        {resume.latestJobTitle || <span className="font-normal text-text/60">Not analyzed yet</span>}
      </Td>
      <Td>{formatDate(resume.uploadedAt)}</Td>
      <Td>
        {resume.latestScores ? (
          <Badge tone="accent">{Math.round(resume.latestScores.overall_match_score)}% match</Badge>
        ) : (
          <Badge tone="neutral">Not analyzed</Badge>
        )}
      </Td>
      <Td>
        {confirmingDelete ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text">Delete?</span>
            <button
              type="button"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              aria-label={`Confirm delete ${resume.filename}`}
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
          <div className="flex items-center gap-1">
            {resume.latestAnalysisId ? (
              <Link
                to={`/analysis-results/${resume.latestAnalysisId}`}
                aria-label={`View analysis for ${resume.filename}`}
                className="inline-flex items-center justify-center rounded-md p-1.5 text-text-h hover:bg-surface"
              >
                <Eye size={16} aria-hidden="true" />
              </Link>
            ) : (
              <span
                className="inline-flex items-center justify-center rounded-md p-1.5 text-text/30"
                title="No analysis yet"
              >
                <Eye size={16} aria-hidden="true" />
              </span>
            )}
            <button
              type="button"
              onClick={handleDownload}
              disabled={downloadMutation.isPending}
              aria-label={`Download ${resume.filename}`}
              className="inline-flex items-center justify-center rounded-md p-1.5 text-text-h hover:bg-surface disabled:opacity-50"
            >
              <Download size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => reanalyzeMutation.mutate()}
              disabled={!resume.latestJobDescriptionId || reanalyzeMutation.isPending}
              aria-label={`Re-analyze ${resume.filename}`}
              title={resume.latestJobDescriptionId ? 'Re-analyze against the same job description' : 'Run an analysis first to enable re-analyzing'}
              className="inline-flex items-center justify-center rounded-md p-1.5 text-accent hover:bg-accent/10 disabled:cursor-not-allowed disabled:text-text/30 disabled:hover:bg-transparent"
            >
              <RefreshCw size={16} className={reanalyzeMutation.isPending ? 'animate-spin' : ''} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              aria-label={`Delete ${resume.filename}`}
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

function ResumesSection() {
  const { data: resumes, isLoading, isError, error, refetch } = useResumeVersions()
  const { showToast } = useToast()
  const bulkDeleteMutation = useBulkDeleteResumes()

  const [collapsed, setCollapsed] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [confirmingBulkDelete, setConfirmingBulkDelete] = useState(false)

  const filteredResumes = useMemo(() => {
    if (!resumes) return []
    const query = search.trim().toLowerCase()
    if (!query) return resumes
    return resumes.filter((resume) => (resume.latestJobTitle || resume.filename || '').toLowerCase().includes(query))
  }, [resumes, search])

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Spinner label="Loading your resumes…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  if (!resumes || resumes.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No resumes uploaded yet"
        description="Upload a resume to start tracking analyses, versions, and match scores."
        action={
          <Link to="/resume/upload" className={buttonClasses()}>
            <Upload size={14} aria-hidden="true" /> Upload a resume
          </Link>
        }
      />
    )
  }

  function toggleSelect(id) {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const allFilteredSelected = filteredResumes.length > 0 && filteredResumes.every((resume) => selectedIds.has(resume.id))

  function toggleSelectAll() {
    setSelectedIds((current) => {
      if (allFilteredSelected) {
        const next = new Set(current)
        filteredResumes.forEach((resume) => next.delete(resume.id))
        return next
      }
      const next = new Set(current)
      filteredResumes.forEach((resume) => next.add(resume.id))
      return next
    })
  }

  async function handleBulkDelete() {
    const ids = Array.from(selectedIds)
    try {
      const { total, failed } = await bulkDeleteMutation.mutateAsync(ids)
      if (failed > 0) {
        showToast(`Deleted ${total - failed} of ${total} resumes — ${failed} failed.`, { tone: 'error' })
      } else {
        showToast(`Deleted ${total} ${total === 1 ? 'resume' : 'resumes'}.`, { tone: 'success' })
      }
    } catch (error) {
      showToast(error.message, { tone: 'error' })
    } finally {
      setSelectedIds(new Set())
      setConfirmingBulkDelete(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative max-w-[220px]">
          <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text/50" aria-hidden="true" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search"
            aria-label="Search resumes by job name"
            className="pl-8 py-1.5 text-sm"
          />
        </div>

        {selectedIds.size > 0 && (
          <div className="ml-auto flex items-center gap-2">
            {confirmingBulkDelete ? (
              <>
                <span className="text-sm text-text">Delete {selectedIds.size} selected?</span>
                <Button variant="danger" size="sm" onClick={handleBulkDelete} isLoading={bulkDeleteMutation.isPending}>
                  <Check size={14} aria-hidden="true" /> Confirm
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setConfirmingBulkDelete(false)} disabled={bulkDeleteMutation.isPending}>
                  Cancel
                </Button>
              </>
            ) : (
              <Button variant="danger" size="sm" onClick={() => setConfirmingBulkDelete(true)}>
                <Trash2 size={14} aria-hidden="true" /> Delete selected ({selectedIds.size})
              </Button>
            )}
          </div>
        )}
      </div>

      {filteredResumes.length === 0 ? (
        <p className="py-6 text-center text-sm text-text">No jobs match "{search}".</p>
      ) : (
        <Table>
          <TableHead>
            {!collapsed && (
              <Th className="w-10">
                <input
                  type="checkbox"
                  checked={allFilteredSelected}
                  onChange={toggleSelectAll}
                  aria-label="Select all resumes"
                  className="h-4 w-4 rounded border-border accent-accent"
                />
              </Th>
            )}
            <Th>
              <div className="flex items-center justify-between gap-2">
                Job
                {collapsed && (
                  <button
                    type="button"
                    onClick={() => setCollapsed((current) => !current)}
                    aria-label="Expand all rows"
                    title="Expand all rows"
                    className="inline-flex items-center justify-center rounded-md p-1 text-text hover:bg-border/40"
                  >
                    <ChevronsUpDown size={14} aria-hidden="true" />
                  </button>
                )}
              </div>
            </Th>
            {!collapsed && <Th>Uploaded</Th>}
            {!collapsed && (
              <Th>
                <div className="flex items-center justify-between gap-2">
                  Status
                  <button
                    type="button"
                    onClick={() => setCollapsed((current) => !current)}
                    aria-label="Collapse all rows"
                    title="Collapse all rows"
                    className="inline-flex items-center justify-center rounded-md p-1 text-text hover:bg-border/40"
                  >
                    <ChevronsUpDown size={14} aria-hidden="true" />
                  </button>
                </div>
              </Th>
            )}
            {!collapsed && (
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            )}
          </TableHead>
          <TableBody>
            {!collapsed &&
              filteredResumes.map((resume) => (
                <ResumeRow
                  key={resume.id}
                  resume={resume}
                  selected={selectedIds.has(resume.id)}
                  onToggleSelect={toggleSelect}
                />
              ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const { data: profile } = useProfile()
  const { data: history, isLoading, isError, error, refetch } = useAnalysisHistory()

  const firstName = (profile?.full_name || profile?.email || '').split(' ')[0].split('@')[0]
  const latest = history?.[0]

  return (
    <div className="flex flex-col gap-8 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Good day{firstName ? `, ${firstName}` : ''}</h1>
        <p className="mt-1 text-sm text-text">
          {latest
            ? `Your latest analysis: ${Math.round(latest.overallScore)}% match · ${history.length} total ${history.length === 1 ? 'analysis' : 'analyses'}.`
            : 'Upload your resume to get your first ATS score and recommendations.'}
        </p>

        <div className="mt-6">
          {isLoading && (
            <div className="flex justify-center py-16">
              <Spinner label="Loading your dashboard…" />
            </div>
          )}

          {isError && <ErrorState message={error.message} onRetry={refetch} />}

          {!isLoading && !isError && !latest && (
            <Card className="flex flex-col items-center gap-4 p-10 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10">
                <Upload size={22} className="text-accent" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-text-h">No analyses yet</h2>
                <p className="mx-auto mt-1 max-w-sm text-sm text-text">
                  Upload your resume and paste a job description to get your ATS score, keyword match, and AI-powered
                  suggestions.
                </p>
              </div>
              <Link to="/resume/upload" className={buttonClasses()}>
                <Upload size={14} aria-hidden="true" /> Analyze my resume <ArrowRight size={13} aria-hidden="true" />
              </Link>
            </Card>
          )}

          {!isLoading && !isError && latest && (
            <Card className="flex flex-col items-center gap-4 p-10 text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-accent/10">
                  <FileText size={22} className="text-accent" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-h">{latest.resumeFilename}</p>
                  <p className="text-sm text-text">{latest.jobTitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <ScoreBadge score={latest.overallScore} />
                <Link to={`/analysis-results/${latest.id}`} className={buttonClasses()}>
                  View results <ArrowRight size={13} aria-hidden="true" />
                </Link>
              </div>
            </Card>
          )}
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-h">Your resumes</h2>
            <p className="mt-0.5 text-sm text-text">Every resume you've uploaded — view, download, re-analyze, or delete.</p>
          </div>
          <Link to="/resume/upload" className={buttonClasses({ variant: 'secondary', size: 'sm' })}>
            <Upload size={14} aria-hidden="true" /> Upload another
          </Link>
        </div>
        <ResumesSection />
      </div>
    </div>
  )
}
