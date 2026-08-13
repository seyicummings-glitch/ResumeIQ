import { useAdminDashboard } from '../../hooks/useAdminData'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import TrendLineChart from '../../components/charts/TrendLineChart'
import MultiSeriesTrendChart from '../../components/charts/MultiSeriesTrendChart'
import ActivityFeed from '../../components/admin/ActivityFeed'

// Real-time updates: this page polls (see useAdminDashboard/useAdminActivityFeed's
// refetchInterval) rather than using a WebSocket. A resume-tooling admin dashboard
// doesn't need sub-second updates, and polling keeps the whole stack on the same
// HTTP+TanStack-Query architecture already used everywhere else in this app instead
// of introducing a second, stateful transport just for this one page.

const SECTIONS = [
  {
    title: 'Users',
    key: 'userAnalytics',
    tiles: [
      { key: 'totalUsers', label: 'Total users' },
      { key: 'activeUsers', label: 'Active users (30d)' },
      { key: 'newUsersToday', label: 'New users today' },
      { key: 'newUsersThisMonth', label: 'New users this month' },
    ],
  },
  {
    title: 'Resume Analytics',
    key: 'resumeAnalytics',
    tiles: [
      { key: 'totalUploads', label: 'Resume uploads' },
      { key: 'totalAnalyses', label: 'Resume analyses' },
      { key: 'totalAtsReports', label: 'ATS reports' },
      { key: 'totalDownloads', label: 'Resume downloads' },
    ],
  },
  {
    title: 'AI Builder Analytics',
    key: 'aiBuilderAnalytics',
    tiles: [
      { key: 'totalBuilds', label: 'AI resume builds' },
      { key: 'totalSaves', label: 'AI resume saves' },
      { key: 'totalDownloads', label: 'AI resume downloads' },
      { key: 'totalRegenerations', label: 'AI regenerations' },
    ],
  },
  {
    title: 'Interview Analytics',
    key: 'interviewAnalytics',
    tiles: [
      { key: 'totalInterviews', label: 'Total interviews' },
      { key: 'voiceInterviews', label: 'Voice interviews' },
      { key: 'textInterviews', label: 'Text interviews' },
      { key: 'completedInterviews', label: 'Completed interviews' },
    ],
  },
  {
    title: 'Learning Analytics',
    key: 'learningAnalytics',
    tiles: [{ key: 'roadmapsGenerated', label: 'Roadmaps generated' }],
  },
  {
    title: 'Revenue Analytics',
    key: 'revenueAnalytics',
    tiles: [
      { key: 'activeSubscribers', label: 'Active subscribers' },
      { key: 'monthlyRevenue', label: 'Monthly revenue', currency: true },
      { key: 'annualRevenue', label: 'Annual revenue', currency: true },
      { key: 'failedPayments', label: 'Failed payments' },
    ],
  },
]

function KpiTile({ label, value, currency }) {
  return (
    <Card className="!p-2">
      <p className="truncate text-[11px] leading-tight text-text">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-text-h">
        {value === null || value === undefined ? '—' : currency ? `$${value.toLocaleString()}` : value.toLocaleString()}
      </p>
    </Card>
  )
}

function TopValuesCard({ title, entries, emptyLabel, tone = 'accent' }) {
  return (
    <Card>
      <h2 className="mb-3 text-base font-semibold text-text-h">{title}</h2>
      <div className="flex flex-wrap gap-2">
        {entries.length === 0 && <p className="text-sm text-text">{emptyLabel}</p>}
        {entries.map((entry) => (
          <Badge key={entry.value} tone={tone}>
            {entry.value} · {entry.count}
          </Badge>
        ))}
      </div>
    </Card>
  )
}

const LEGACY_CHARTS = [
  { key: 'userGrowth', title: 'User growth (daily, 30d)', yKey: 'count', label: 'New users' },
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

  const { charts } = data

  const allTiles = SECTIONS.flatMap((section) =>
    section.tiles.map((tile) => ({ ...tile, id: `${section.key}.${tile.key}`, value: data[section.key][tile.key] }))
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 lg:grid-cols-8">
        {allTiles.map((tile) => (
          <KpiTile key={tile.id} label={tile.label} value={tile.value} currency={tile.currency} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">User growth</h2>
          <MultiSeriesTrendChart
            data={charts.userGrowthDaily}
            xKey="date"
            series={[{ key: 'count', label: 'New users (daily)', color: 'var(--color-accent)' }]}
          />
        </Card>

        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">Platform usage — most used features</h2>
          <div className="flex flex-wrap gap-2">
            {charts.platformUsage.length === 0 && <p className="text-sm text-text">No activity recorded yet.</p>}
            {charts.platformUsage.map((entry) => (
              <Badge key={entry.feature} tone="accent">
                {entry.feature.replace(/_/g, ' ')} · {entry.count}
              </Badge>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">Resume analytics — uploads, analyses, downloads</h2>
          <MultiSeriesTrendChart
            data={charts.resumeActivity}
            xKey="date"
            series={[
              { key: 'uploads', label: 'Uploads', color: 'var(--color-accent)' },
              { key: 'analyses', label: 'Analyses', color: 'var(--color-success)' },
              { key: 'downloads', label: 'Downloads', color: 'var(--color-warning)' },
            ]}
          />
        </Card>

        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">Interview analytics — started vs. completed</h2>
          <MultiSeriesTrendChart
            data={charts.interviewStartedVsCompleted}
            xKey="date"
            series={[
              { key: 'started', label: 'Started', color: 'var(--color-accent-2)' },
              { key: 'completed', label: 'Completed', color: 'var(--color-success)' },
            ]}
          />
        </Card>

        <TopValuesCard title="Learning analytics — top skills viewed" entries={charts.topSkillsViewed} emptyLabel="No skills viewed yet." tone="accent" />

        <Card>
          <h2 className="mb-2 text-base font-semibold text-text-h">Subscription analytics — revenue trend</h2>
          <MultiSeriesTrendChart
            data={charts.revenueTrend}
            xKey="date"
            series={[{ key: 'revenue', label: 'Revenue ($)', color: 'var(--color-success)' }]}
          />
        </Card>

        {LEGACY_CHARTS.map(({ key, title, yKey, label }) => (
          <Card key={key}>
            <h2 className="mb-2 text-base font-semibold text-text-h">{title}</h2>
            <TrendLineChart data={charts[key]} xKey="date" yKey={yKey} label={label} />
          </Card>
        ))}

        <TopValuesCard title="Learning analytics — most opened courses" entries={data.learningAnalytics.mostOpenedCourses} emptyLabel="No courses opened yet." tone="success" />
        <TopValuesCard title="Learning analytics — most opened YouTube resources" entries={data.learningAnalytics.mostOpenedYoutubeResources} emptyLabel="No video resources opened yet." tone="warning" />
        <TopValuesCard title="Most requested job roles" entries={charts.mostRequestedJobRoles.map((r) => ({ value: r.role, count: r.count }))} emptyLabel="No job descriptions saved yet." tone="accent" />
        <TopValuesCard title="Most common missing skills" entries={charts.mostCommonMissingSkills.map((r) => ({ value: r.skill, count: r.count }))} emptyLabel="No analyses yet." tone="danger" />

        <ActivityFeed />
      </div>
    </div>
  )
}
