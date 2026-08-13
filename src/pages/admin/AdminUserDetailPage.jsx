import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useAdminUserDetail } from '../../hooks/useAdminData'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import { Tabs } from '../../components/ui/Tabs'
import { buttonClasses } from '../../components/ui/Button'

const STATUS_TONE = { active: 'success', deactivated: 'warning', deleted: 'danger' }

const TABS = [
  { id: 'profile', label: 'Profile' },
  { id: 'resumes', label: 'Resumes' },
  { id: 'analyses', label: 'Analyses' },
  { id: 'interviews', label: 'Interviews' },
  { id: 'skillAssessments', label: 'Skill assessments' },
  { id: 'roadmaps', label: 'Learning roadmaps' },
]

const ACTIVITY_TAB_COUNT_KEY = {
  resumes: 'resumes',
  analyses: 'analyses',
  interviews: 'interviewSessions',
  skillAssessments: 'skillAssessments',
  roadmaps: 'learningRoadmaps',
}

function formatDate(value) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function ProfileField({ label, value }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-text/60">{label}</p>
      <p className="mt-0.5 text-sm text-text-h">{value || '—'}</p>
    </div>
  )
}

export default function AdminUserDetailPage() {
  const { id } = useParams()
  const [activeTab, setActiveTab] = useState('profile')
  const { data: user, isLoading, isError, error, refetch } = useAdminUserDetail(id)

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading user…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-4">
      <Link to="/admin/users" className={buttonClasses({ variant: 'ghost', size: 'sm', className: 'w-fit' })}>
        <ArrowLeft size={16} aria-hidden="true" />
        Back to users
      </Link>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-text-h">{user.fullName || user.email}</h1>
            <p className="text-sm text-text">{user.email}</p>
          </div>
          <div className="flex gap-2">
            <Badge tone={user.role === 'admin' ? 'accent' : 'neutral'}>{user.role}</Badge>
            <Badge tone={STATUS_TONE[user.status] || 'neutral'}>{user.status}</Badge>
            <Badge tone="neutral">{user.subscriptionPlan || 'free'}</Badge>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <ProfileField label="Country" value={user.country} />
          <ProfileField label="Registered" value={formatDate(user.createdAt)} />
          <ProfileField label="Last login" value={formatDate(user.lastLoginAt)} />
          <ProfileField label="Total activity" value={user.totalActivity} />
        </div>
      </Card>

      <Card>
        <Tabs tabs={TABS} activeId={activeTab} onChange={setActiveTab}>
          {activeTab === 'profile' ? (
            <p className="text-sm text-text">
              This user has {user.counts.resumes} resume{user.counts.resumes === 1 ? '' : 's'}, {user.counts.analyses} analys
              {user.counts.analyses === 1 ? 'is' : 'es'}, {user.counts.interviewSessions} interview session
              {user.counts.interviewSessions === 1 ? '' : 's'}, {user.counts.skillAssessments} skill assessment
              {user.counts.skillAssessments === 1 ? '' : 's'}, and {user.counts.learningRoadmaps} learning roadmap
              {user.counts.learningRoadmaps === 1 ? '' : 's'} on file.
            </p>
          ) : (
            <p className="text-sm text-text">
              {user.counts[ACTIVITY_TAB_COUNT_KEY[activeTab]]} record{user.counts[ACTIVITY_TAB_COUNT_KEY[activeTab]] === 1 ? '' : 's'} on
              file. A detailed, browsable list lands here as this section of the admin panel is built out.
            </p>
          )}
        </Tabs>
      </Card>
    </div>
  )
}
