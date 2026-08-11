import { useAdminDashboard } from '../../hooks/useAdminData'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import TrendLineChart from '../../components/charts/TrendLineChart'

const KPI_LABELS = {
  totalUsers: 'Total users',
  activeUsersToday: 'Active users today',
  newUsersThisMonth: 'New users this month',
  totalResumesUploaded: 'Resumes uploaded',
  totalAnalyses: 'Resume analyses',
  totalAiResumeBuilds: 'AI resume builds',
  totalSkillAssessments: 'Skill assessments',
  totalInterviewSessions: 'Interview sessions',
  totalRoadmapsGenerated: 'Learning roadmaps',
  totalDocumentsGenerated: 'Documents generated',
  aiRequestsToday: 'AI requests today',
  averageMatchScore: 'Average match score',
}

const CHARTS = [
  { key: 'userGrowth', title: 'User growth', yKey: 'count', label: 'New users' },
  { key: 'resumeUploadActivity', title: 'Resume upload activity', yKey: 'count', label: 'Resumes uploaded', color: 'var(--color-accent-2)' },
  { key: 'analysisActivity', title: 'Analysis activity', yKey: 'count', label: 'Analyses', color: 'var(--color-success)' },
  { key: 'interviewActivity', title: 'Interview activity', yKey: 'count', label: 'Interview sessions', color: 'var(--color-warning)' },
  { key: 'skillAssessmentActivity', title: 'Skill assessment activity', yKey: 'count', label: 'Assessments taken' },
]

export default function AdminDashboardPage() {
  const { data, isLoading, isError, error, refetch } = useAdminDashboard()

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading dashboard…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  const { kpis, charts } = data

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {Object.entries(KPI_LABELS).map(([key, label]) => (
          <Card key={key}>
            <p className="text-sm text-text">{label}</p>
            <p className="mt-1 text-2xl font-semibold text-text-h">
              {kpis[key] === null || kpis[key] === undefined
                ? '—'
                : key === 'averageMatchScore'
                  ? `${kpis[key]}%`
                  : kpis[key]}
            </p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {CHARTS.map(({ key, title, yKey, label, color }) => (
          <Card key={key}>
            <h2 className="mb-2 text-base font-semibold text-text-h">{title}</h2>
            <TrendLineChart data={charts[key]} xKey="date" yKey={yKey} label={label} color={color} />
          </Card>
        ))}

        <Card>
          <h2 className="mb-3 text-base font-semibold text-text-h">Most requested job roles</h2>
          <div className="flex flex-wrap gap-2">
            {charts.mostRequestedJobRoles.length === 0 && <p className="text-sm text-text">No job descriptions saved yet.</p>}
            {charts.mostRequestedJobRoles.map((entry) => (
              <Badge key={entry.role} tone="accent">
                {entry.role} · {entry.count}
              </Badge>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 text-base font-semibold text-text-h">Most common missing skills</h2>
          <div className="flex flex-wrap gap-2">
            {charts.mostCommonMissingSkills.length === 0 && <p className="text-sm text-text">No analyses yet.</p>}
            {charts.mostCommonMissingSkills.map((entry) => (
              <Badge key={entry.skill} tone="danger">
                {entry.skill} · {entry.count}
              </Badge>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
