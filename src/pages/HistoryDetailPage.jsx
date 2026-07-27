import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useAnalysisDetail } from '../hooks/useAnalysisHistory'
import Card from '../components/ui/Card'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import Badge from '../components/ui/Badge'
import ScoreGauge from '../components/charts/ScoreGauge'
import ScoreBreakdownBars from '../components/charts/ScoreBreakdownBars'

export default function HistoryDetailPage() {
  const { id } = useParams()
  const { data, isLoading, isError, error, refetch } = useAnalysisDetail(id)

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading analysis…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState title="Couldn't load this analysis" message={error.message} onRetry={refetch} />
  }

  const breakdownItems = [
    { label: 'Skills', score: data.skillMatch.skill_score },
    { label: 'Experience', score: data.experienceMatch.experience_score },
    { label: 'Qualifications', score: data.qualificationMatch.qualification_score },
  ]

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 py-8">
      <Link to="/history" className="inline-flex w-fit items-center gap-1 text-sm text-accent hover:underline">
        <ArrowLeft size={16} aria-hidden="true" /> Back to history
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-text-h">{data.jobTitle}</h1>
        <p className="mt-1 text-sm text-text">
          {data.resumeFilename} · {new Intl.DateTimeFormat(undefined, { dateStyle: 'long', timeStyle: 'short' }).format(new Date(data.analyzedAt))}
        </p>
      </div>

      <Card className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <ScoreGauge score={data.overallScore} label="Overall score" />
        <div className="flex-1">
          <ScoreBreakdownBars items={breakdownItems} />
          <div className="mt-4 flex flex-wrap gap-1.5">
            {data.skillMatch.matched_skills.map((skill) => (
              <Badge key={skill} tone="success">
                {skill}
              </Badge>
            ))}
            {data.skillMatch.missing_skills.map((skill) => (
              <Badge key={skill} tone="danger">
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
