import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Map,
  Clock,
  Target,
  Layers,
  ChevronDown,
  ChevronUp,
  CircleCheck,
  Circle,
  ExternalLink,
  Flag,
  RotateCcw,
  Sparkles,
  FolderKanban,
  Dumbbell,
} from 'lucide-react'
import clsx from 'clsx'
import { useLearningRoadmap, useToggleRoadmapTopic, useRegenerateRoadmap } from '../hooks/useLearningRoadmap'
import Card from '../components/ui/Card'
import Button, { buttonClasses } from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import { useToast } from '../components/ui/Toast'

const PRIORITY_TONE = {
  critical: 'danger',
  high: 'warning',
  medium: 'neutral',
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

function SourceBadge({ source }) {
  if (source === 'ai') {
    return (
      <Badge tone="accent">
        <Sparkles size={11} aria-hidden="true" /> AI-powered
      </Badge>
    )
  }
  return <Badge tone="neutral">Rule-based</Badge>
}

function TopicRow({ topic, onToggle, isToggling }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border-b border-border last:border-b-0">
      <div className="flex items-start gap-3 px-4 py-3">
        <button
          type="button"
          onClick={() => onToggle(topic.topic_key)}
          disabled={isToggling}
          aria-label={topic.done ? `Mark ${topic.title} as not done` : `Mark ${topic.title} as done`}
          className="mt-0.5 shrink-0 text-text hover:text-accent disabled:opacity-50"
        >
          {topic.done ? <CircleCheck size={20} className="text-success" aria-hidden="true" /> : <Circle size={20} aria-hidden="true" />}
        </button>

        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="flex flex-1 items-center justify-between gap-3 text-left"
        >
          <div>
            <p className={clsx('font-medium text-text-h', topic.done && 'text-text/50 line-through')}>{topic.title}</p>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs text-text">
              <Badge tone={PRIORITY_TONE[topic.priority] || 'neutral'} className="!text-[10px]">
                {topic.priority}
              </Badge>
              {topic.estimated_hours}h estimated
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
        <div className="flex flex-col gap-4 px-4 pb-4 pl-11">
          <p className="text-sm text-text">{topic.why_it_matters}</p>

          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">Learning objectives</p>
            <ul className="flex flex-col gap-1 text-sm text-text">
              {topic.learning_objectives.map((objective, index) => (
                <li key={index}>• {objective}</li>
              ))}
            </ul>
          </div>

          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">Resources</p>
            <ul className="flex flex-col gap-1.5">
              {topic.resources.map((resource, index) => (
                <li key={index} className="flex items-start gap-1.5 text-sm text-text">
                  <ExternalLink size={13} className="mt-0.5 shrink-0 text-accent" aria-hidden="true" />
                  <span>
                    {resource.name} <span className="text-text/60">— {resource.type} · {resource.provider}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">
                <FolderKanban size={12} aria-hidden="true" /> Projects
              </p>
              <ul className="flex flex-col gap-1 text-sm text-text">
                {topic.projects.map((project, index) => (
                  <li key={index}>• {project}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">
                <Dumbbell size={12} aria-hidden="true" /> Practical exercises
              </p>
              <ul className="flex flex-col gap-1 text-sm text-text">
                {topic.exercises.map((exercise, index) => (
                  <li key={index}>• {exercise}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StageCard({ stage, onToggleTopic, isToggling }) {
  const doneCount = stage.topics.filter((t) => t.done).length

  return (
    <Card className="p-0">
      <div className="border-b border-border px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-text-h">{stage.stage}</h2>
          <span className="text-xs text-text">
            {doneCount}/{stage.topics.length} complete · {stage.estimated_duration}
          </span>
        </div>
        <p className="mt-1 text-sm text-text">{stage.description}</p>
        <div className="mt-3 flex items-start gap-2 rounded-md bg-accent/10 p-3">
          <Flag size={14} className="mt-0.5 shrink-0 text-accent" aria-hidden="true" />
          <p className="text-sm text-text-h">
            <span className="font-semibold">Milestone: </span>
            {stage.milestone}
          </p>
        </div>
      </div>
      <div>
        {stage.topics.map((topic) => (
          <TopicRow key={topic.topic_key} topic={topic} onToggle={onToggleTopic} isToggling={isToggling} />
        ))}
      </div>
    </Card>
  )
}

export default function LearningRoadmapPage() {
  const { data, isLoading, isError, error, refetch } = useLearningRoadmap()
  const toggleMutation = useToggleRoadmapTopic()
  const regenerateMutation = useRegenerateRoadmap()
  const { showToast } = useToast()

  async function handleRegenerate() {
    try {
      await regenerateMutation.mutateAsync()
      showToast('Generated a new roadmap.', { tone: 'success' })
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

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

  if (!data.has_context) {
    return (
      <div className="py-8">
        <h1 className="mb-6 text-2xl font-semibold text-text-h">Learning roadmap</h1>
        <EmptyState
          icon={Map}
          title="Set a target role or save an analysis first"
          description="Your roadmap is built primarily around the target role and industry in your profile — set those, or save a resume analysis, to unlock a personalized plan."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Link to="/profile" className={buttonClasses()}>
                Set target role
              </Link>
              <Link to="/dashboard" className={buttonClasses({ variant: 'secondary' })}>
                Go to dashboard
              </Link>
            </div>
          }
        />
      </div>
    )
  }

  const { roadmap } = data
  const { stages, stats } = roadmap
  const progressPct = stats.total_count > 0 ? Math.round((stats.done_count / stats.total_count) * 100) : 0

  return (
    <div className="flex flex-col gap-6 py-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold text-text-h">Learning roadmap</h1>
            <SourceBadge source={roadmap.source} />
          </div>
          <p className="mt-1 text-sm text-text">
            {roadmap.target_role ? (
              <>
                A complete path to becoming job-ready as a <span className="font-medium text-text-h">{roadmap.target_role}</span>
                {roadmap.industry ? <> in {roadmap.industry}</> : null}.
              </>
            ) : (
              'A phased plan to close the skill gaps from your latest analysis.'
            )}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={handleRegenerate} isLoading={regenerateMutation.isPending}>
          <RotateCcw size={14} aria-hidden="true" />
          Regenerate roadmap
        </Button>
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
        <StatCard icon={Target} label="Topics" value={stats.total_count} />
        <StatCard icon={Layers} label="Stages" value={stages.length} />
      </div>

      {stages.map((stage) => (
        <StageCard
          key={stage.stage}
          stage={stage}
          onToggleTopic={(topicKey) => toggleMutation.mutate({ topicKey })}
          isToggling={toggleMutation.isPending}
        />
      ))}
    </div>
  )
}
