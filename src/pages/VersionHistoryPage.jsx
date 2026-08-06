import { useEffect, useMemo, useState } from 'react'
import { GitCompare, ArrowUp, ArrowDown, Minus, History as HistoryIcon, Download } from 'lucide-react'
import { useResumeVersions, useCompareResumeVersions, useDownloadResume } from '../hooks/useResumeVersions'
import { useToast } from '../components/ui/Toast'
import { Table, TableHead, Th, TableBody, Td } from '../components/ui/Table'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Select from '../components/ui/Select'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import Button from '../components/ui/Button'

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function versionOptionLabel(version) {
  const base = version.label || `Version ${version.version}`
  return `${base} — ${version.filename}`
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

function ScoreCompareCard({ label, versionA, versionB }) {
  const scoreA = versionA.latestScores?.overall_match_score
  const scoreB = versionB.latestScores?.overall_match_score
  const delta = scoreA !== undefined && scoreA !== null && scoreB !== undefined && scoreB !== null ? scoreA - scoreB : null

  return (
    <Card className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-text-h">{label}</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-text">{versionA.label || `v${versionA.version}`}</p>
          <p className="text-2xl font-semibold text-text-h">
            {scoreA !== undefined && scoreA !== null ? Math.round(scoreA) : '—'}
          </p>
        </div>
        <div>
          <p className="text-xs text-text">{versionB.label || `v${versionB.version}`}</p>
          <p className="text-2xl font-semibold text-text-h">
            {scoreB !== undefined && scoreB !== null ? Math.round(scoreB) : '—'}
          </p>
        </div>
      </div>
      <DeltaIndicator delta={delta} />
    </Card>
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

function VersionListRow({ version, onDownload, isDownloading }) {
  return (
    <tr>
      <Td>
        <div className="flex items-center gap-2">
          <span className="font-medium">{version.label || `v${version.version}`}</span>
          {version.isActive && <Badge tone="accent">Current</Badge>}
        </div>
      </Td>
      <Td>{version.filename}</Td>
      <Td>{formatDate(version.uploadedAt)}</Td>
      <Td>
        {version.skills.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {version.skills.slice(0, 6).map((skill) => (
              <Badge key={skill} tone="neutral">
                {skill}
              </Badge>
            ))}
            {version.skills.length > 6 && <Badge tone="neutral">+{version.skills.length - 6} more</Badge>}
          </div>
        ) : (
          <span className="text-sm text-text">No skills detected</span>
        )}
      </Td>
      <Td>
        {version.latestScores ? (
          <Badge tone="accent">{Math.round(version.latestScores.overall_match_score)} match</Badge>
        ) : (
          <span className="text-sm text-text">No analysis yet</span>
        )}
      </Td>
      <Td>
        <Button variant="secondary" size="sm" onClick={onDownload} isLoading={isDownloading} title="Download this version">
          <Download size={14} aria-hidden="true" />
        </Button>
      </Td>
    </tr>
  )
}

export default function VersionHistoryPage() {
  const { data: versions, isLoading, isError, error, refetch } = useResumeVersions()
  const { showToast } = useToast()
  const downloadMutation = useDownloadResume()
  const [downloadingId, setDownloadingId] = useState(null)
  const [mode, setMode] = useState('list')
  const [aId, setAId] = useState(null)
  const [bId, setBId] = useState(null)

  function handleDownload(version) {
    setDownloadingId(version.id)
    downloadMutation.mutate(
      { resumeId: version.id, filename: version.filename },
      {
        onSettled: () => setDownloadingId(null),
        onError: (err) => showToast(err.message, { tone: 'error' }),
      }
    )
  }

  useEffect(() => {
    if (versions && versions.length >= 2 && (aId === null || bId === null)) {
      setAId(versions[0].id)
      setBId(versions[1].id)
    }
  }, [versions, aId, bId])

  const canCompare = (versions?.length || 0) >= 2

  const {
    data: comparison,
    isLoading: compareLoading,
    isError: compareError,
    error: compareErrorObj,
  } = useCompareResumeVersions(mode === 'compare' ? aId : null, mode === 'compare' ? bId : null)

  const otherOptionsForA = useMemo(() => versions || [], [versions])
  const otherOptionsForB = useMemo(() => versions || [], [versions])

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading resume versions…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 py-8">
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-h">Resume version history</h1>
          <p className="mt-1 text-sm text-text">Every saved version of your resume, with match scores where available.</p>
        </div>
        {canCompare && (
          <Button
            variant={mode === 'compare' ? 'primary' : 'secondary'}
            onClick={() => setMode(mode === 'compare' ? 'list' : 'compare')}
          >
            <GitCompare size={16} aria-hidden="true" /> {mode === 'compare' ? 'Back to list' : 'Compare versions'}
          </Button>
        )}
      </div>

      {(versions?.length || 0) === 0 ? (
        <EmptyState
          icon={HistoryIcon}
          title="No resume versions yet"
          description="Save a resume to start building version history."
        />
      ) : mode === 'list' ? (
        <Table>
          <TableHead>
            <Th>Version</Th>
            <Th>Filename</Th>
            <Th>Uploaded</Th>
            <Th>Skills</Th>
            <Th>Latest score</Th>
            <Th>Download</Th>
          </TableHead>
          <TableBody>
            {versions.map((version) => (
              <VersionListRow
                key={version.id}
                version={version}
                onDownload={() => handleDownload(version)}
                isDownloading={downloadingId === version.id}
              />
            ))}
          </TableBody>
        </Table>
      ) : (
        <div className="flex flex-col gap-6">
          <Card className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Select label="Version A" value={aId ?? ''} onChange={(event) => setAId(Number(event.target.value))}>
              {otherOptionsForA.map((version) => (
                <option key={version.id} value={version.id}>
                  {versionOptionLabel(version)}
                </option>
              ))}
            </Select>
            <Select label="Version B" value={bId ?? ''} onChange={(event) => setBId(Number(event.target.value))}>
              {otherOptionsForB.map((version) => (
                <option key={version.id} value={version.id}>
                  {versionOptionLabel(version)}
                </option>
              ))}
            </Select>
          </Card>

          {aId === bId && (
            <p className="text-sm text-warning">Choose two different versions to compare.</p>
          )}

          {compareLoading && aId !== bId && (
            <div className="flex justify-center py-8">
              <Spinner label="Loading comparison…" />
            </div>
          )}

          {compareError && <ErrorState message={compareErrorObj.message} />}

          {comparison && aId !== bId && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <ScoreCompareCard label="Overall match score" versionA={comparison.resumeA} versionB={comparison.resumeB} />
              </div>

              {comparison.skillDiff ? (
                <Card className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <SkillChipList title="Gaps closed" skills={comparison.skillDiff.resolved} tone="success" />
                  <SkillChipList title="Still missing" skills={comparison.skillDiff.remaining} tone="warning" />
                  <SkillChipList title="New gaps" skills={comparison.skillDiff.added} tone="danger" />
                </Card>
              ) : (
                <Card>
                  <p className="text-sm text-text">
                    Not enough analysis data to compare skill gaps for these two versions — run a match analysis on
                    both first.
                  </p>
                </Card>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
