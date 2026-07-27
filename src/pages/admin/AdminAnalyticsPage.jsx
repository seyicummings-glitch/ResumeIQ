import { useAdminAnalytics } from '../../hooks/useAdminData'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import TrendLineChart from '../../components/charts/TrendLineChart'

const STAT_LABELS = {
  totalUsers: 'Total users',
  totalResumesAnalyzed: 'Resumes analyzed',
  totalJobDescriptions: 'Job descriptions saved',
  averageMatchScore: 'Average match score',
}

export default function AdminAnalyticsPage() {
  const { data, isLoading, isError, error, refetch } = useAdminAnalytics()

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading analytics…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning">
        Demo data: shown for illustration until the backend exposes real analytics endpoints.
      </p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Object.entries(STAT_LABELS).map(([key, label]) => (
          <Card key={key}>
            <p className="text-sm text-text">{label}</p>
            <p className="mt-1 text-2xl font-semibold text-text-h">{data.summary[key]}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">Signups over time</h2>
          <TrendLineChart data={data.signupsOverTime} xKey="date" yKey="signups" label="Signups" />
        </Card>
        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">Analyses per day</h2>
          <TrendLineChart data={data.analysesPerDay} xKey="date" yKey="analyses" label="Analyses" color="var(--color-success)" />
        </Card>
        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">Average match score trend</h2>
          <TrendLineChart data={data.averageScoreTrend} xKey="date" yKey="averageScore" label="Avg. score" color="var(--color-warning)" />
        </Card>
        <Card>
          <h2 className="mb-3 text-base font-semibold text-text-h">Most common missing skills</h2>
          <div className="flex flex-wrap gap-2">
            {data.topMissingSkills.map((entry) => (
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
