import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileClock as HistoryIcon, Download, Trash2, Check, X, GitCompare, ArrowUp, ArrowDown, Minus, ChevronsUpDown } from 'lucide-react'
import { useAnalysisHistory, useDeleteAnalysis, useCompareAnalyses } from '../hooks/useAnalysisHistory'
import { useGenerateDocument } from '../hooks/useDocuments'
import { getScoreBand } from '../lib/scoreBands'
import { Table, TableHead, Th, TableBody, Td } from '../components/ui/Table'
import Select from '../components/ui/Select'
import Input from '../components/ui/Input'
import ScoreBadge from '../components/ui/ScoreBadge'
import Badge from '../components/ui/Badge'
import Card from '../components/ui/Card'
import Button, { buttonClasses } from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import { useToast } from '../components/ui/Toast'

const BAND_FILTERS = [
  { value: 'all', label: 'All scores' },
  { value: 'success', label: 'Strong (75+)' },
  { value: 'warning', label: 'Fair (50-74)' },
  { value: 'danger', label: 'Needs work (<50)' },
]

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

function DeltaIndicator({ delta }) {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return null
  if (Math.abs(delta) < 0.05) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-text">
        <Minus size={14} aria-hidden="true" /> No change
      </span>
    )
  }
  const isUp = delta > 0
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${isUp ? 'text-success' : 'text-danger'}`}>
      {isUp ? <ArrowUp size={14} aria-hidden="true" /> : <ArrowDown size={14} aria-hidden="true" />}
      {isUp ? '+' : ''}
      {delta.toFixed(1)} pts
    </span>
  )
}

function SkillChipList({ title, skills, tone }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-text-h">{title}</p>
      {skills.length === 0 ? (
        <p className="text-sm text-text">None</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {skills.map((skill) => (
            <Badge key={skill} tone={tone}>
              {skill}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

function HistoryRow({ record, onDeleted }) {
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const generateMutation = useGenerateDocument()
  const deleteMutation = useDeleteAnalysis()
  const { showToast } = useToast()

  async function handleDownload() {
    try {
      await generateMutation.mutateAsync({ analysisId: record.id })
      showToast('PDF report generated and downloaded.', { tone: 'success' })
    } catch (error) {
      showToast(error.message, { tone: 'error' })
    }
  }

  async function handleConfirmDelete() {
    try {
      await deleteMutation.mutateAsync(record.id)
      showToast('Analysis deleted.', { tone: 'success' })
      onDeleted?.()
    } catch (error) {
      showToast(error.message, { tone: 'error' })
    } finally {
      setConfirmingDelete(false)
    }
  }

  return (
    <tr>
      <Td>{formatDate(record.analyzedAt)}</Td>
      <Td>{record.resumeFilename}</Td>
      <Td>{record.jobTitle}</Td>
      <Td>
        <ScoreBadge score={record.overallScore} />
      </Td>
      <Td>
        {confirmingDelete ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text">Delete?</span>
            <button
              type="button"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              aria-label="Confirm delete analysis"
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
            <Link
              to={`/analysis-results/${record.id}`}
              className="rounded-md px-2 py-1.5 text-sm font-medium text-accent hover:underline"
            >
              View
            </Link>
            <button
              type="button"
              onClick={handleDownload}
              disabled={generateMutation.isPending}
              aria-label="Download PDF report"
              className="inline-flex items-center justify-center rounded-md p-1.5 text-text-h hover:bg-surface disabled:opacity-50"
            >
              <Download size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              aria-label="Delete analysis"
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

function CompareView({ records }) {
  const [aId, setAId] = useState(records[0]?.id ?? null)
  const [bId, setBId] = useState(records[1]?.id ?? null)
  const { data: comparison, isLoading, isError, error } = useCompareAnalyses(aId, bId)

  const scoreA = comparison?.analysis_a?.overall_match_score
  const scoreB = comparison?.analysis_b?.overall_match_score
  const delta = scoreA !== undefined && scoreA !== null && scoreB !== undefined && scoreB !== null ? scoreA - scoreB : null

  return (
    <div className="flex flex-col gap-6">
      <Card className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select label="Analysis A" value={aId ?? ''} onChange={(event) => setAId(Number(event.target.value))}>
          {records.map((record) => (
            <option key={record.id} value={record.id}>
              {formatDate(record.analyzedAt)} — {record.resumeFilename} · {record.jobTitle}
            </option>
          ))}
        </Select>
        <Select label="Analysis B" value={bId ?? ''} onChange={(event) => setBId(Number(event.target.value))}>
          {records.map((record) => (
            <option key={record.id} value={record.id}>
              {formatDate(record.analyzedAt)} — {record.resumeFilename} · {record.jobTitle}
            </option>
          ))}
        </Select>
      </Card>

      {aId === bId && <p className="text-sm text-warning">Choose two different analyses to compare.</p>}

      {isLoading && aId !== bId && (
        <div className="flex justify-center py-8">
          <Spinner label="Loading comparison…" />
        </div>
      )}

      {isError && <ErrorState message={error.message} />}

      {comparison && aId !== bId && (
        <div className="flex flex-col gap-4">
          <Card className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-text-h">Overall match score</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-text">{comparison.analysis_a.resume_filename}</p>
                <p className="text-2xl font-semibold text-text-h">{scoreA !== undefined && scoreA !== null ? Math.round(scoreA) : '—'}</p>
              </div>
              <div>
                <p className="text-xs text-text">{comparison.analysis_b.resume_filename}</p>
                <p className="text-2xl font-semibold text-text-h">{scoreB !== undefined && scoreB !== null ? Math.round(scoreB) : '—'}</p>
              </div>
            </div>
            <DeltaIndicator delta={delta} />
          </Card>

          <Card className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <SkillChipList title="Gaps closed" skills={comparison.skill_diff.resolved} tone="success" />
            <SkillChipList title="Still missing" skills={comparison.skill_diff.remaining} tone="warning" />
            <SkillChipList title="New gaps" skills={comparison.skill_diff.added} tone="danger" />
          </Card>
        </div>
      )}
    </div>
  )
}

export default function HistoryPage() {
  const { data, isLoading, isError, error, refetch } = useAnalysisHistory()
  const [bandFilter, setBandFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [mode, setMode] = useState('list')
  const [collapsed, setCollapsed] = useState(false)

  const filtered = useMemo(() => {
    if (!data) return []
    let rows = [...data].sort((a, b) => new Date(b.analyzedAt) - new Date(a.analyzedAt))

    if (bandFilter !== 'all') {
      rows = rows.filter((record) => getScoreBand(record.overallScore).tone === bandFilter)
    }

    const query = search.trim().toLowerCase()
    if (query) {
      rows = rows.filter(
        (record) =>
          record.resumeFilename?.toLowerCase().includes(query) || record.jobTitle?.toLowerCase().includes(query)
      )
    }

    if (dateFrom) {
      const fromTime = new Date(dateFrom).getTime()
      rows = rows.filter((record) => new Date(record.analyzedAt).getTime() >= fromTime)
    }
    if (dateTo) {
      const toTime = new Date(dateTo).getTime() + 24 * 60 * 60 * 1000 - 1
      rows = rows.filter((record) => new Date(record.analyzedAt).getTime() <= toTime)
    }

    return rows
  }, [data, bandFilter, search, dateFrom, dateTo])

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading analysis history…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  const canCompare = data.length >= 2

  return (
    <div className="flex flex-col gap-6 py-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-text-h">Analysis history</h1>
          <p className="mt-1 text-sm text-text">A permanent archive of every resume-to-job match you've run.</p>
        </div>
        {canCompare && (
          <Button
            variant={mode === 'compare' ? 'primary' : 'secondary'}
            onClick={() => setMode(mode === 'compare' ? 'list' : 'compare')}
          >
            <GitCompare size={16} aria-hidden="true" /> {mode === 'compare' ? 'Back to list' : 'Compare analyses'}
          </Button>
        )}
      </div>

      {data.length === 0 ? (
        <EmptyState
          icon={HistoryIcon}
          title="No analyses yet"
          description="Run a match on your dashboard to start building history."
          action={
            <Link to="/dashboard" className={buttonClasses()}>
              Go to dashboard
            </Link>
          }
        />
      ) : mode === 'compare' ? (
        <CompareView records={[...data].sort((a, b) => new Date(b.analyzedAt) - new Date(a.analyzedAt))} />
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[220px] flex-1">
              <Input
                label="Search"
                placeholder="Resume filename or job title…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <div className="w-44">
              <Select label="Filter by score" value={bandFilter} onChange={(event) => setBandFilter(event.target.value)}>
                {BAND_FILTERS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-40">
              <Input label="From" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            </div>
            <div className="w-40">
              <Input label="To" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            </div>
          </div>

          {filtered.length === 0 ? (
            <EmptyState icon={HistoryIcon} title="No analyses match your filters" description="Try adjusting your search, score filter, or date range." />
          ) : (
            <Table>
              <TableHead>
                {collapsed ? (
                  <Th>
                    <div className="flex items-center justify-between gap-2">
                      Job title
                      <button
                        type="button"
                        onClick={() => setCollapsed((current) => !current)}
                        aria-label="Expand all rows"
                        title="Expand all rows"
                        className="inline-flex items-center justify-center rounded-md p-1 text-text hover:bg-border/40"
                      >
                        <ChevronsUpDown size={14} aria-hidden="true" />
                      </button>
                    </div>
                  </Th>
                ) : (
                  <>
                    <Th>Date</Th>
                    <Th>Resume</Th>
                    <Th>Job title</Th>
                    <Th>
                      <div className="flex items-center justify-between gap-2">
                        Score
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
                    <Th>
                      <span className="sr-only">Actions</span>
                    </Th>
                  </>
                )}
              </TableHead>
              <TableBody>
                {!collapsed &&
                  filtered.map((record) => <HistoryRow key={record.id} record={record} onDeleted={refetch} />)}
              </TableBody>
            </Table>
          )}
        </>
      )}
    </div>
  )
}
