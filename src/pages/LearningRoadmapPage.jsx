import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Map, Clock, Target, Layers, ChevronDown, ChevronUp, CircleCheck, Circle, ExternalLink } from 'lucide-react'
import clsx from 'clsx'
import { useLearningRoadmap, useToggleRoadmapItem } from '../hooks/useLearningRoadmap'
import Card from '../components/ui/Card'
import { buttonClasses } from '../components/ui/Button'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'

const IMPORTANCE_TONE = {
  critical: 'text-danger',
  high: 'text-warning',
  medium: 'text-text',
}

function StatCard({ icon: Icon, label, value }) {
  return (
    <Card className="flex items-center gap-3">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/10">
        <Icon size={18} className="text-accent" aria-hidden="true" />
      </div>
      <div>
        <p className="text-lg font-semibold text-text-h">{value}</p>
        <p className="text-xs text-text">{label}</p>
      </div>
    </Card>
  )
}

function RoadmapItemRow({ item, onToggle, isToggling }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border-b border-border last:border-b-0">
      <div className="flex items-start gap-3 px-4 py-3">
        <button
          type="button"
          onClick={() => onToggle(item.skill)}
          disabled={isToggling}
          aria-label={item.done ? `Mark ${item.skill} as not done` : `Mark ${item.skill} as done`}
          className="mt-0.5 shrink-0 text-text hover:text-accent disabled:opacity-50"
        >
          {item.done ? <CircleCheck size={20} className="text-success" aria-hidden="true" /> : <Circle size={20} aria-hidden="true" />}
        </button>

        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="flex flex-1 items-center justify-between gap-3 text-left"
        >
          <div>
            <p className={clsx('font-medium text-text-h', item.done && 'text-text/50 line-through')}>{item.skill}</p>
            <p className="mt-0.5 text-xs text-text">
              <span className={clsx('font-semibold', IMPORTANCE_TONE[item.importance])}>{item.importance}</span>
              {' · '}
              {item.type} · {item.provider} · {item.duration}
            </p>
          </div>
          {expanded ? (
            <ChevronUp size={16} className="shrink-0 text-text" aria-hidden="true" />
          ) : (
            <ChevronDown size={16} className="shrink-0 text-text" aria-hidden="true" />
          )}
        </button>
      </div>

      {expanded && (
        <div className="px-4 pb-4 pl-11">
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">Resources</p>
          <ul className="flex flex-col gap-1.5">
            {item.resources.map((resource) => (
              <li key={resource} className="flex items-start gap-1.5 text-sm text-text">
                <ExternalLink size={13} className="mt-0.5 shrink-0 text-accent" aria-hidden="true" />
                <span>{resource}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function LearningRoadmapPage() {
  const { data, isLoading, isError, error, refetch } = useLearningRoadmap()
  const toggleMutation = useToggleRoadmapItem()

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading your learning roadmap…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  if (!data.has_gaps) {
    return (
      <div className="py-8">
        <h1 className="mb-6 text-2xl font-semibold text-text-h">Learning roadmap</h1>
        <EmptyState
          icon={Map}
          title="No skill gaps detected, or analyze a resume first"
          description="Save an analysis from your dashboard to get a personalized skill-gap learning roadmap."
          action={
            <Link to="/dashboard" className={buttonClasses()}>
              Go to dashboard
            </Link>
          }
        />
      </div>
    )
  }

  const { phases, stats } = data
  const progressPct = stats.total_count > 0 ? Math.round((stats.done_count / stats.total_count) * 100) : 0

  return (
    <div className="flex flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Learning roadmap</h1>
        <p className="mt-1 text-sm text-text">A phased plan to close the skill gaps from your latest analysis.</p>
      </div>

      <Card>
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-text-h">Overall progress</span>
          <span className="text-text">
            {stats.done_count} / {stats.total_count} complete
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-border/40">
          <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${progressPct}%` }} />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={Clock} label="Estimated hours" value={stats.total_hours} />
        <StatCard icon={Target} label="Skill gaps" value={stats.total_count} />
        <StatCard icon={Layers} label="Phases" value={phases.length} />
      </div>

      {phases.map((phase) => (
        <Card key={phase.phase} className="p-0">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-base font-semibold text-text-h">{phase.phase}</h2>
            <span className="text-xs text-text">{phase.timeframe}</span>
          </div>
          <div>
            {phase.items.map((item) => (
              <RoadmapItemRow
                key={item.skill}
                item={item}
                onToggle={(skill) => toggleMutation.mutate({ skill })}
                isToggling={toggleMutation.isPending}
              />
            ))}
          </div>
        </Card>
      ))}
    </div>
  )
}
