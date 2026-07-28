import { useMemo, useState } from 'react'
import { X, ChevronDown, ChevronUp, Lightbulb, Eye, EyeOff } from 'lucide-react'
import clsx from 'clsx'
import { useInterviewQuestions } from '../hooks/useInterviewQuestions'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'

const CATEGORIES = ['All', 'Behavioral', 'Technical', 'System Design', 'Role-Specific']

const DIFFICULTY_TONE = {
  Easy: 'success',
  Medium: 'warning',
  Hard: 'danger',
}

function QuestionCard({ question }) {
  const [expanded, setExpanded] = useState(false)
  const [showSample, setShowSample] = useState(false)
  const [answer, setAnswer] = useState('')

  return (
    <Card className="p-0">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex-1">
          <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
            <Badge tone="accent">{question.category}</Badge>
            <Badge tone={DIFFICULTY_TONE[question.difficulty] || 'neutral'}>{question.difficulty}</Badge>
          </div>
          <p className="font-medium text-text-h">{question.question}</p>
        </div>
        {expanded ? (
          <ChevronUp size={18} className="mt-1 shrink-0 text-text" aria-hidden="true" />
        ) : (
          <ChevronDown size={18} className="mt-1 shrink-0 text-text" aria-hidden="true" />
        )}
      </button>

      {expanded && (
        <div className="flex flex-col gap-4 border-t border-border px-4 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-text/70">Why this question</p>
            <p className="mt-1 text-sm text-text">{question.relevance}</p>
          </div>

          <div className="flex gap-2 rounded-lg bg-accent/[0.08] px-3 py-2.5">
            <Lightbulb size={16} className="mt-0.5 shrink-0 text-accent" aria-hidden="true" />
            <p className="text-sm text-text">{question.tip}</p>
          </div>

          <div>
            <label htmlFor={`answer-${question.id}`} className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-text/70">
              Your practice answer
            </label>
            <textarea
              id={`answer-${question.id}`}
              rows={5}
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder="Type your answer here to practice out loud or in writing…"
              className="w-full resize-y rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-h placeholder:text-text/50 focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <Button variant="secondary" size="sm" onClick={() => setShowSample((value) => !value)}>
              {showSample ? <EyeOff size={14} aria-hidden="true" /> : <Eye size={14} aria-hidden="true" />}
              {showSample ? 'Hide sample answer' : 'Show sample answer'}
            </Button>
            {showSample && (
              <p className="mt-3 rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-text">
                {question.sample_answer}
              </p>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}

export default function InterviewPracticePage() {
  const { data, isLoading, isError, error, refetch } = useInterviewQuestions()
  const [activeCategory, setActiveCategory] = useState('All')
  const [bannerDismissed, setBannerDismissed] = useState(false)

  const filteredQuestions = useMemo(() => {
    if (!data) return []
    if (activeCategory === 'All') return data.questions
    return data.questions.filter((q) => q.category === activeCategory)
  }, [data, activeCategory])

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading interview questions…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Interview practice</h1>
        <p className="mt-1 text-sm text-text">
          Practice questions tailored to your latest resume-to-job match, plus universal behavioral and system design
          questions.
        </p>
      </div>

      {!data.has_analysis && !bannerDismissed && (
        <div className="flex items-center justify-between gap-3 rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning">
          <span>Showing general questions — save an analysis from your dashboard for personalized ones.</span>
          <button
            type="button"
            onClick={() => setBannerDismissed(true)}
            aria-label="Dismiss"
            className="shrink-0 text-warning hover:opacity-70"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      )}

      {data.has_analysis && data.jd_title && (
        <p className="text-sm text-text">
          Personalized for: <span className="font-medium text-text-h">{data.jd_title}</span>
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => setActiveCategory(category)}
            className={clsx(
              'rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
              activeCategory === category
                ? 'bg-accent text-accent-contrast'
                : 'border border-border text-text hover:bg-border/40 hover:text-text-h'
            )}
          >
            {category}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {filteredQuestions.map((question) => (
          <QuestionCard key={question.id} question={question} />
        ))}
        {filteredQuestions.length === 0 && (
          <p className="py-8 text-center text-sm text-text">No questions in this category.</p>
        )}
      </div>
    </div>
  )
}
