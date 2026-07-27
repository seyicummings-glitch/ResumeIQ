import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileClock as HistoryIcon } from 'lucide-react'
import { useAnalysisHistory } from '../hooks/useAnalysisHistory'
import { getScoreBand } from '../lib/scoreBands'
import { Table, TableHead, Th, TableBody, Td } from '../components/ui/Table'
import Select from '../components/ui/Select'
import ScoreBadge from '../components/ui/ScoreBadge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import { buttonClasses } from '../components/ui/Button'

const BAND_FILTERS = [
  { value: 'all', label: 'All scores' },
  { value: 'success', label: 'Strong (75+)' },
  { value: 'warning', label: 'Fair (50-74)' },
  { value: 'danger', label: 'Needs work (<50)' },
]

export default function HistoryPage() {
  const { data, isLoading, isError, error, refetch } = useAnalysisHistory()
  const [bandFilter, setBandFilter] = useState('all')

  const filtered = useMemo(() => {
    if (!data) return []
    const sorted = [...data].sort((a, b) => new Date(b.analyzedAt) - new Date(a.analyzedAt))
    if (bandFilter === 'all') return sorted
    return sorted.filter((record) => getScoreBand(record.overallScore).tone === bandFilter)
  }, [data, bandFilter])

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

  return (
    <div className="flex flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Analysis history</h1>
        <p className="mt-1 text-sm text-text">Past resume-to-job matches, most recent first.</p>
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
      ) : (
        <>
          <div className="max-w-xs">
            <Select label="Filter by score" value={bandFilter} onChange={(event) => setBandFilter(event.target.value)}>
              {BAND_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>

          <Table>
            <TableHead>
              <Th>Date</Th>
              <Th>Resume</Th>
              <Th>Job title</Th>
              <Th>Score</Th>
              <Th>
                <span className="sr-only">View</span>
              </Th>
            </TableHead>
            <TableBody>
              {filtered.map((record) => (
                <tr key={record.id}>
                  <Td>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(record.analyzedAt))}</Td>
                  <Td>{record.resumeFilename}</Td>
                  <Td>{record.jobTitle}</Td>
                  <Td>
                    <ScoreBadge score={record.overallScore} />
                  </Td>
                  <Td>
                    <Link to={`/history/${record.id}`} className="font-medium text-accent hover:underline">
                      View details
                    </Link>
                  </Td>
                </tr>
              ))}
            </TableBody>
          </Table>
        </>
      )}
    </div>
  )
}
