import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { Brain, CheckCircle2, XCircle, Lightbulb, RotateCcw, ArrowRight } from 'lucide-react'
import { useSkillAssessmentBuild, useSubmitSkillAssessment } from '../hooks/useSkillAssessment'
import Card from '../components/ui/Card'
import Button, { buttonClasses } from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import TextArea from '../components/ui/TextArea'
import ScoreBreakdownBars from '../components/charts/ScoreBreakdownBars'
import { getScoreBand, SCORE_BAND_COLORS } from '../lib/scoreBands'

const MIN_SOFT_ANSWER_WORDS = 30

const DIFFICULTY_TONE = {
  beginner: 'success',
  intermediate: 'warning',
  advanced: 'danger',
}

function wordCount(text) {
  return text.trim() ? text.trim().split(/\s+/).length : 0
}

function IntroPhase({ build, onBegin }) {
  if (!build.has_analysis) {
    return (
      <EmptyState
        icon={Brain}
        title="Save an analysis first"
        description="Skill Assessment personalizes questions from your latest saved resume-to-job match. Run and save an analysis on your dashboard to unlock it."
        action={
          <Link to="/dashboard" className={buttonClasses()}>
            Go to dashboard
          </Link>
        }
      />
    )
  }

  return (
    <Card className="flex flex-col items-center gap-5 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
        <Brain size={28} className="text-accent" aria-hidden="true" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-text-h">Ready to test your skills?</h2>
        <p className="mt-1 max-w-md text-sm text-text">
          A personalized quiz built from your resume's skills and the gaps found in your latest analysis, followed by a
          few open-ended scenario questions.
        </p>
      </div>

      {build.detected_categories.length > 0 && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {build.detected_categories.map((category) => (
            <Badge key={category} tone="accent">
              {category}
            </Badge>
          ))}
        </div>
      )}

      <div className="flex gap-6 text-sm text-text">
        <div>
          <div className="text-xl font-semibold text-text-h">{build.questions.length}</div>
          <div>Technical questions</div>
        </div>
        <div>
          <div className="text-xl font-semibold text-text-h">{build.soft_scenarios.length}</div>
          <div>Soft-skill scenarios</div>
        </div>
      </div>

      <Button onClick={onBegin} disabled={build.questions.length === 0}>
        Begin assessment
        <ArrowRight size={16} aria-hidden="true" />
      </Button>
    </Card>
  )
}

function TechnicalPhase({ questions, onComplete }) {
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState(null)
  const [answers, setAnswers] = useState({})

  const question = questions[index]
  const hasAnswered = selected !== null
  const isLast = index === questions.length - 1

  function selectOption(optionIndex) {
    if (hasAnswered) return
    setSelected(optionIndex)
    setAnswers((prev) => ({ ...prev, [question.id]: optionIndex }))
  }

  function goNext() {
    if (isLast) {
      onComplete({ ...answers, [question.id]: selected })
      return
    }
    setIndex((value) => value + 1)
    setSelected(null)
  }

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text">
          Question {index + 1} of {questions.length}
        </span>
        <Badge tone={DIFFICULTY_TONE[question.difficulty] || 'neutral'}>{question.difficulty}</Badge>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-border/40">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${((index + (hasAnswered ? 1 : 0)) / questions.length) * 100}%` }}
        />
      </div>

      <div>
        <Badge tone="neutral" className="mb-2">
          {question.category_label}
        </Badge>
        <h2 className="text-base font-semibold text-text-h">{question.question}</h2>
      </div>

      <div className="flex flex-col gap-2.5">
        {question.options.map((option, optionIndex) => {
          const isCorrectOption = optionIndex === question.correct_index
          const isSelectedOption = optionIndex === selected

          let toneClass = 'border-border hover:border-accent/60 hover:bg-surface'
          if (hasAnswered) {
            if (isCorrectOption) {
              toneClass = 'border-success bg-success-bg text-success'
            } else if (isSelectedOption) {
              toneClass = 'border-danger bg-danger-bg text-danger'
            } else {
              toneClass = 'border-border opacity-60'
            }
          }

          return (
            <button
              key={optionIndex}
              type="button"
              onClick={() => selectOption(optionIndex)}
              disabled={hasAnswered}
              className={clsx(
                'flex items-center justify-between gap-3 rounded-md border px-4 py-3 text-left text-sm font-medium text-text-h transition-colors disabled:cursor-not-allowed',
                toneClass
              )}
            >
              <span>{option}</span>
              {hasAnswered && isCorrectOption && <CheckCircle2 size={18} className="shrink-0 text-success" aria-hidden="true" />}
              {hasAnswered && !isCorrectOption && isSelectedOption && (
                <XCircle size={18} className="shrink-0 text-danger" aria-hidden="true" />
              )}
            </button>
          )
        })}
      </div>

      {hasAnswered && (
        <div className="flex flex-col gap-3 rounded-md border border-border bg-bg p-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-h">Explanation</p>
            <p className="mt-1 text-sm text-text">{question.explanation}</p>
          </div>
          <div className="flex items-start gap-2">
            <Lightbulb size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
            <p className="text-sm text-text">{question.tip}</p>
          </div>
        </div>
      )}

      {hasAnswered && (
        <Button onClick={goNext} className="w-fit self-end">
          {isLast ? 'Continue to soft-skill scenarios' : 'Next question'}
          <ArrowRight size={16} aria-hidden="true" />
        </Button>
      )}
    </Card>
  )
}

function SoftPhase({ scenarios, isSubmitting, onComplete }) {
  const [index, setIndex] = useState(0)
  const [texts, setTexts] = useState(() => scenarios.map(() => ''))

  const scenario = scenarios[index]
  const isLast = index === scenarios.length - 1
  const words = wordCount(texts[index])
  const canProceed = words >= MIN_SOFT_ANSWER_WORDS

  function updateText(value) {
    setTexts((prev) => prev.map((text, i) => (i === index ? value : text)))
  }

  function goNext() {
    if (isLast) {
      onComplete(texts)
      return
    }
    setIndex((value) => value + 1)
  }

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text">
          Scenario {index + 1} of {scenarios.length}
        </span>
        <Badge tone="accent">{scenario.category}</Badge>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-border/40">
        <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${(index / scenarios.length) * 100}%` }} />
      </div>

      <p className="text-base font-medium text-text-h">{scenario.scenario}</p>

      <TextArea
        label="Your answer"
        rows={7}
        value={texts[index]}
        onChange={(event) => updateText(event.target.value)}
        placeholder="Walk through your thinking — there's no single right answer, but concrete detail scores better than a one-line response."
        hint={`${words} / ${MIN_SOFT_ANSWER_WORDS} words minimum`}
      />

      <Button onClick={goNext} disabled={!canProceed} isLoading={isLast && isSubmitting} className="w-fit self-end">
        {isLast ? 'View results' : 'Next scenario'}
        <ArrowRight size={16} aria-hidden="true" />
      </Button>
    </Card>
  )
}

function ResultsPhase({ result, onRetake }) {
  const band = getScoreBand(result.overall_score)
  const bandColors = SCORE_BAND_COLORS[band.tone]

  const breakdownItems = result.category_breakdown.map((entry) => ({
    label: entry.category_label,
    score: entry.pct,
  }))

  return (
    <div className="flex flex-col gap-6">
      <Card className="flex flex-col items-center gap-3 text-center">
        <p className="text-sm font-medium text-text">Overall score</p>
        <div className={clsx('text-5xl font-bold', bandColors.text)}>{result.overall_score}</div>
        <Badge tone={band.tone}>{band.label}</Badge>
        <p className="text-sm text-text">
          {result.correct_count} of {result.total} technical questions correct
        </p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="flex flex-col gap-1">
          <p className="text-sm font-medium text-text">Technical score</p>
          <p className="text-2xl font-semibold text-text-h">{result.technical_score}</p>
        </Card>
        <Card className="flex flex-col gap-1">
          <p className="text-sm font-medium text-text">Soft-skill score</p>
          <p className="text-2xl font-semibold text-text-h">{result.soft_score}</p>
        </Card>
      </div>

      {breakdownItems.length > 0 && (
        <Card>
          <h2 className="mb-3 text-base font-semibold text-text-h">Category breakdown</h2>
          <ScoreBreakdownBars items={breakdownItems} caption="Percent correct per matched skill category." />
        </Card>
      )}

      <Button variant="secondary" onClick={onRetake} className="w-fit">
        <RotateCcw size={16} aria-hidden="true" />
        Retake assessment
      </Button>
    </div>
  )
}

export default function SkillAssessmentPage() {
  const [phase, setPhase] = useState('intro')
  const buildQuery = useSkillAssessmentBuild()
  const submitMutation = useSubmitSkillAssessment()
  const [technicalAnswers, setTechnicalAnswers] = useState({})
  const [result, setResult] = useState(null)

  const questionIds = useMemo(() => buildQuery.data?.questions.map((q) => q.id) || [], [buildQuery.data])

  function handleTechnicalComplete(answers) {
    setTechnicalAnswers(answers)
    setPhase('soft')
  }

  function handleSoftComplete(softAnswerTexts) {
    submitMutation.mutate(
      { questionIds, technicalAnswers: technicalAnswers, softAnswerTexts },
      {
        onSuccess: (data) => {
          setResult(data)
          setPhase('results')
        },
      }
    )
  }

  function handleRetake() {
    setTechnicalAnswers({})
    setResult(null)
    setPhase('intro')
    buildQuery.refetch()
  }

  return (
    <div className="flex flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Skill assessment</h1>
        <p className="mt-1 text-sm text-text">
          Technical questions matched to your resume's skills and gaps, plus a few soft-skill scenarios.
        </p>
      </div>

      {buildQuery.isLoading && (
        <div className="flex justify-center py-16">
          <Spinner label="Building your assessment…" />
        </div>
      )}

      {buildQuery.isError && <ErrorState message={buildQuery.error.message} onRetry={buildQuery.refetch} />}

      {buildQuery.isSuccess && phase === 'intro' && (
        <IntroPhase build={buildQuery.data} onBegin={() => setPhase('technical')} />
      )}

      {buildQuery.isSuccess && phase === 'technical' && (
        <TechnicalPhase questions={buildQuery.data.questions} onComplete={handleTechnicalComplete} />
      )}

      {buildQuery.isSuccess && phase === 'soft' && (
        <SoftPhase
          scenarios={buildQuery.data.soft_scenarios}
          isSubmitting={submitMutation.isPending}
          onComplete={handleSoftComplete}
        />
      )}

      {submitMutation.isError && <p className="text-sm text-danger">{submitMutation.error.message}</p>}

      {phase === 'results' && result && <ResultsPhase result={result} onRetake={handleRetake} />}
    </div>
  )
}
