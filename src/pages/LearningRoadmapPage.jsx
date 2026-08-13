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
  CircleX,
  Circle,
  ExternalLink,
  Flag,
  RotateCcw,
  Sparkles,
  FolderKanban,
  Dumbbell,
  GraduationCap,
  HelpCircle,
  MessageCircle,
  Play,
  BookOpen,
  FileText,
} from 'lucide-react'
import clsx from 'clsx'
import { useLearningRoadmap, useToggleRoadmapTopic, useRegenerateRoadmap } from '../hooks/useLearningRoadmap'
import { trackRoadmapResourceClick } from '../api/roadmap'
import { useCareerCoachContext } from '../coach/CareerCoachContext'
import Card from '../components/ui/Card'
import Button, { buttonClasses } from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import { useToast } from '../components/ui/Toast'

const MILESTONE_LEVELS = [
  { key: 'beginner', label: 'Beginner' },
  { key: 'intermediate', label: 'Intermediate' },
  { key: 'advanced', label: 'Advanced' },
]

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

function MilestoneTrack({ milestones }) {
  if (!milestones) return null
  return (
    <div>
      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">
        <GraduationCap size={12} aria-hidden="true" /> Milestones
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {MILESTONE_LEVELS.map(({ key, label }) => (
          <div key={key} className="rounded-lg bg-surface p-2.5">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-accent">{label}</p>
            <p className="text-xs text-text-h">{milestones[key]}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function QuizQuestion({ question, index }) {
  const [selected, setSelected] = useState(null)
  const isAnswered = selected !== null
  const isCorrect = selected === question.correct_index

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="mb-2 text-sm font-medium text-text-h">
        {index + 1}. {question.question}
      </p>
      <div className="flex flex-col gap-1.5">
        {question.options.map((option, optionIndex) => {
          const isSelected = selected === optionIndex
          const isRightAnswer = optionIndex === question.correct_index
          return (
            <button
              key={optionIndex}
              type="button"
              onClick={() => !isAnswered && setSelected(optionIndex)}
              disabled={isAnswered}
              className={clsx(
                'rounded-md border px-3 py-1.5 text-left text-sm transition-colors disabled:cursor-default',
                !isAnswered && 'border-border hover:border-accent hover:bg-accent/5',
                isAnswered && isRightAnswer && 'border-success bg-success-bg text-success',
                isAnswered && isSelected && !isRightAnswer && 'border-danger bg-danger-bg text-danger',
                isAnswered && !isSelected && !isRightAnswer && 'border-border text-text/50'
              )}
            >
              {option}
            </button>
          )
        })}
      </div>
      {isAnswered && (
        <p className={clsx('mt-2 flex items-start gap-1.5 text-xs', isCorrect ? 'text-success' : 'text-danger')}>
          {isCorrect ? (
            <CircleCheck size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          ) : (
            <CircleX size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          )}
          <span>{question.explanation}</span>
        </p>
      )}
    </div>
  )
}

function VideoResourceCard({ links, skillTitle }) {
  if (!links.youtubeUrl) return null
  const description = links.exactMatch
    ? `A focused tutorial on ${skillTitle}${links.youtubeChannel ? ` from ${links.youtubeChannel}` : ''}${links.youtubeDuration ? ` (${links.youtubeDuration})` : ''}.`
    : `No exact video for "${skillTitle}" yet — this is the closest match for your field${links.youtubeChannel ? ` from ${links.youtubeChannel}` : ''}.`

  return (
    <a
      href={links.youtubeUrl}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => trackRoadmapResourceClick({ resourceType: 'video', skillTitle, url: links.youtubeUrl })}
      className="group flex w-full flex-col overflow-hidden rounded-lg border border-border bg-surface transition-colors hover:border-accent sm:w-56"
    >
      {links.youtubeThumbnailUrl ? (
        <div className="relative aspect-video w-full shrink-0 overflow-hidden bg-black/10">
          <img
            src={links.youtubeThumbnailUrl}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
            onError={(event) => {
              event.currentTarget.parentElement.style.display = 'none'
            }}
          />
          <div className="absolute inset-0 flex items-center justify-center bg-black/25 opacity-0 transition-opacity group-hover:opacity-100">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-danger">
              <Play size={16} className="ml-0.5" fill="currentColor" aria-hidden="true" />
            </span>
          </div>
          {links.youtubeDuration && (
            <span className="absolute bottom-1 right-1 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-medium text-white">
              {links.youtubeDuration}
            </span>
          )}
          {!links.exactMatch && (
            <span className="absolute left-1 top-1 rounded bg-accent/90 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-white">
              Closest match
            </span>
          )}
        </div>
      ) : (
        <div className="flex aspect-video w-full shrink-0 items-center justify-center bg-danger-bg text-danger">
          <Play size={22} aria-hidden="true" />
        </div>
      )}
      <div className="flex flex-1 flex-col gap-1 p-2.5">
        <p className="line-clamp-2 text-xs font-medium text-text-h">{links.youtubeTitle || 'Recommended tutorial'}</p>
        {links.youtubeChannel && <p className="text-[11px] text-text/60">{links.youtubeChannel}</p>}
        <p className="line-clamp-2 text-[11px] text-text/70">{description}</p>
        <span className="mt-auto inline-flex items-center gap-1 pt-1 text-[11px] font-semibold text-accent">
          Start Learning <ExternalLink size={11} aria-hidden="true" />
        </span>
      </div>
    </a>
  )
}

function CourseResourceCard({ links, skillTitle }) {
  if (!links.courseUrl) return null
  return (
    <a
      href={links.courseUrl}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => trackRoadmapResourceClick({ resourceType: 'course', skillTitle, url: links.courseUrl })}
      className="flex w-full flex-col gap-2 rounded-lg border border-border bg-surface p-2.5 transition-colors hover:border-accent sm:w-56"
    >
      <div className="flex items-start gap-2">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent">
          <BookOpen size={16} aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="line-clamp-2 text-xs font-medium text-text-h">{links.courseTitle || 'Recommended course'}</p>
          {links.courseProvider && <p className="text-[11px] text-text/60">{links.courseProvider}</p>}
        </div>
      </div>
      <span className="mt-auto inline-flex items-center gap-1 text-[11px] font-semibold text-accent">
        Start Course <ExternalLink size={11} aria-hidden="true" />
      </span>
    </a>
  )
}

function RecommendedResourceLinks({ links, skillTitle }) {
  if (!links) return null
  const hasVideo = Boolean(links.youtubeUrl)
  const hasCourse = Boolean(links.courseUrl)
  if (!hasVideo && !hasCourse && !links.docsUrl) return null

  return (
    <div className="flex flex-wrap items-stretch gap-2" onClick={(event) => event.stopPropagation()}>
      <VideoResourceCard links={links} skillTitle={skillTitle} />
      <CourseResourceCard links={links} skillTitle={skillTitle} />
      {links.docsUrl && (
        <a
          href={links.docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => trackRoadmapResourceClick({ resourceType: 'docs', skillTitle, url: links.docsUrl })}
          className="inline-flex h-fit items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-xs font-medium text-text-h transition-colors hover:border-accent hover:text-accent"
        >
          <FileText size={12} aria-hidden="true" />
          Documentation
        </a>
      )}
    </div>
  )
}

function TopicRow({ topic, onToggle, isToggling, onAskCoach }) {
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

        <div className="flex-1">
          <button
            type="button"
            onClick={() => {
              const nextExpanded = !expanded
              setExpanded(nextExpanded)
              if (nextExpanded) trackRoadmapResourceClick({ resourceType: 'skill', skillTitle: topic.title })
            }}
            aria-expanded={expanded}
            className="flex w-full items-center justify-between gap-3 text-left"
          >
            <div>
              <p className={clsx('font-medium text-text-h', topic.done && 'text-text/50 line-through')}>{topic.title}</p>
              <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-text">
                <Badge tone={PRIORITY_TONE[topic.priority] || 'neutral'} className="!text-[10px]">
                  {topic.priority}
                </Badge>
                {topic.category && (
                  <Badge tone="accent" className="!text-[10px]">
                    {topic.category}
                  </Badge>
                )}
                {topic.estimated_hours}h estimated
              </p>
            </div>
            {expanded ? (
              <ChevronUp size={16} className="shrink-0 text-text" aria-hidden="true" />
            ) : (
              <ChevronDown size={16} className="shrink-0 text-text" aria-hidden="true" />
            )}
          </button>

          {topic.current_gap && <p className="mt-1.5 text-xs text-text">{topic.current_gap}</p>}

          <div className="mt-2">
            <RecommendedResourceLinks links={topic.resource_links} skillTitle={topic.title} />
          </div>
        </div>
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

          <MilestoneTrack milestones={topic.milestones} />

          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">More resources</p>
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

          {topic.quiz && topic.quiz.length > 0 && (
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">
                <HelpCircle size={12} aria-hidden="true" /> Self-check quiz
              </p>
              <div className="flex flex-col gap-2">
                {topic.quiz.map((question, index) => (
                  <QuizQuestion key={index} question={question} index={index} />
                ))}
              </div>
            </div>
          )}

          {onAskCoach && (
            <Button variant="secondary" size="sm" className="w-fit" onClick={() => onAskCoach(topic)}>
              <MessageCircle size={14} aria-hidden="true" /> Ask the Coach about this topic
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

function StageCard({ stage, onToggleTopic, isToggling, onAskCoach }) {
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
          <TopicRow
            key={topic.topic_key}
            topic={topic}
            onToggle={onToggleTopic}
            isToggling={isToggling}
            onAskCoach={onAskCoach}
          />
        ))}
      </div>
    </Card>
  )
}

export default function LearningRoadmapPage() {
  const { data, isLoading, isError, error, refetch } = useLearningRoadmap()
  const toggleMutation = useToggleRoadmapTopic()
  const regenerateMutation = useRegenerateRoadmap()
  const { openCoach } = useCareerCoachContext()
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
          {roadmap.detected_profession && (
            <p className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-text">
              <span className="text-text/70">Detected profession:</span>
              <Badge tone="accent">{roadmap.detected_profession}</Badge>
              {roadmap.detected_industry && <Badge tone="neutral">{roadmap.detected_industry}</Badge>}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => openCoach(null)}>
            <MessageCircle size={14} aria-hidden="true" />
            AI Career Coach
          </Button>
          <Button variant="secondary" size="sm" onClick={handleRegenerate} isLoading={regenerateMutation.isPending}>
            <RotateCcw size={14} aria-hidden="true" />
            Regenerate roadmap
          </Button>
        </div>
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
          onAskCoach={openCoach}
        />
      ))}
    </div>
  )
}
