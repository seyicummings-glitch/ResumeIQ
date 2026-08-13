import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import {
  Brain,
  CheckCircle2,
  XCircle,
  Lightbulb,
  RotateCcw,
  ArrowRight,
  Sparkles,
  AlertCircle,
} from 'lucide-react'
import { useSkillAssessmentBuild, useSubmitSkillAssessment } from '../hooks/useSkillAssessment'
import { QUESTION_COUNT_OPTIONS, DEFAULT_QUESTION_COUNT } from '../api/skillAssessment'
import Card from '../components/ui/Card'
import Button, { buttonClasses } from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import TextArea from '../components/ui/TextArea'
import ScoreBreakdownBars from '../components/charts/ScoreBreakdownBars'
import { getScoreBand, SCORE_BAND_COLORS } from '../lib/scoreBands'

const DIFFICULTY_TONE = {
  beginner: 'success',
  intermediate: 'warning',
  advanced: 'danger',
}

const SOFT_QUESTION_TYPES = new Set(['scenario', 'behavioral'])

const TYPE_LABELS = {
  technical: 'Technical',
  scenario: 'Scenario',
  problem_solving: 'Problem Solving',
  behavioral: 'Behavioral',
}

function typeLabel(type) {
  return TYPE_LABELS[type] || type
}

function wordCount(text) {
  return text && text.trim() ? text.trim().split(/\s+/).length : 0
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

function QuestionCountPicker({ value, onChange, disabled }) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text/70">Number of questions</p>
      <div className="flex items-center gap-1 rounded-md border border-border p-0.5">
        {QUESTION_COUNT_OPTIONS.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            disabled={disabled}
            className={clsx(
              'rounded px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50',
              value === option ? 'bg-accent text-accent-contrast' : 'text-text/70 hover:text-text-h'
            )}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}

function IntroPhase({ build, onBegin, questionCount, onQuestionCountChange }) {
  if (!build.has_context) {
    return (
      <EmptyState
        icon={Brain}
        title="Set a target role or save an analysis first"
        description="Skill Assessment is built primarily around the target role and industry in your profile — set those, or save a resume analysis, to unlock a personalized assessment."
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
    )
  }

  const coreCount = build.questions.filter((q) => !SOFT_QUESTION_TYPES.has(q.type)).length
  const softCount = build.questions.filter((q) => SOFT_QUESTION_TYPES.has(q.type)).length

  return (
    <Card className="flex flex-col items-center gap-5 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
        <Brain size={28} className="text-accent" aria-hidden="true" />
      </div>
      <div>
        <div className="mb-2 flex items-center justify-center gap-2">
          <h2 className="text-lg font-semibold text-text-h">Ready to test your skills?</h2>
          <SourceBadge source={build.source} />
        </div>
        <p className="mt-1 max-w-md text-sm text-text">
          {build.source === 'ai'
            ? 'Interview-level questions generated from your resume’s skills, projects, and gaps against the job — graded by AI with detailed feedback on every answer.'
            : 'A randomized technical quiz matched to your resume’s skills and gaps, plus scenario-based questions — AI grading is currently unavailable, so scoring uses rule-based checks instead.'}
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

      <QuestionCountPicker value={questionCount} onChange={onQuestionCountChange} />

      <div className="flex gap-6 text-sm text-text">
        <div>
          <div className="text-xl font-semibold text-text-h">{coreCount}</div>
          <div>Technical &amp; problem-solving</div>
        </div>
        <div>
          <div className="text-xl font-semibold text-text-h">{softCount}</div>
          <div>Scenario &amp; behavioral</div>
        </div>
      </div>

      <Button onClick={onBegin} disabled={build.questions.length === 0}>
        Begin assessment
        <ArrowRight size={16} aria-hidden="true" />
      </Button>
    </Card>
  )
}

function QuestionPhase({ questions, onComplete, isSubmitting }) {
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [selectedOption, setSelectedOption] = useState(null)
  const [textValue, setTextValue] = useState('')

  const question = questions[index]
  const isLast = index === questions.length - 1
  const isMultipleChoice = question.input_type === 'multiple_choice'
  const hasAnsweredMc = isMultipleChoice && selectedOption !== null
  const words = wordCount(textValue)
  const canProceedText = !isMultipleChoice && textValue.trim().length > 0

  function selectOption(optionIndex) {
    if (hasAnsweredMc) return
    setSelectedOption(optionIndex)
  }

  function goNext() {
    const answer = isMultipleChoice
      ? { questionId: question.id, answerIndex: selectedOption }
      : { questionId: question.id, answerText: textValue.trim() }
    const nextAnswers = { ...answers, [question.id]: answer }
    setAnswers(nextAnswers)

    if (isLast) {
      onComplete(Object.values(nextAnswers))
      return
    }
    setIndex((value) => value + 1)
    setSelectedOption(null)
    setTextValue('')
  }

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text">
          Question {index + 1} of {questions.length}
        </span>
        <div className="flex items-center gap-2">
          <Badge tone="accent">{typeLabel(question.type)}</Badge>
          {question.difficulty && (
            <Badge tone={DIFFICULTY_TONE[question.difficulty] || 'neutral'}>{question.difficulty}</Badge>
          )}
        </div>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-border/40">
        <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${(index / questions.length) * 100}%` }} />
      </div>

      <div>
        <Badge tone="neutral" className="mb-2">
          {question.category}
        </Badge>
        <h2 className="text-base font-semibold text-text-h">{question.question}</h2>
      </div>

      {isMultipleChoice ? (
        <>
          <div className="flex flex-col gap-2.5">
            {question.options.map((option, optionIndex) => {
              const isCorrectOption = optionIndex === question.correct_index
              const isSelectedOption = optionIndex === selectedOption

              let toneClass = 'border-border hover:border-accent/60 hover:bg-surface'
              if (hasAnsweredMc) {
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
                  disabled={hasAnsweredMc}
                  className={clsx(
                    'flex items-center justify-between gap-3 rounded-md border px-4 py-3 text-left text-sm font-medium text-text-h transition-colors disabled:cursor-not-allowed',
                    toneClass
                  )}
                >
                  <span>{option}</span>
                  {hasAnsweredMc && isCorrectOption && <CheckCircle2 size={18} className="shrink-0 text-success" aria-hidden="true" />}
                  {hasAnsweredMc && !isCorrectOption && isSelectedOption && (
                    <XCircle size={18} className="shrink-0 text-danger" aria-hidden="true" />
                  )}
                </button>
              )
            })}
          </div>

          {hasAnsweredMc && (
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

          {hasAnsweredMc && (
            <Button onClick={goNext} isLoading={isLast && isSubmitting} className="w-fit self-end">
              {isLast ? 'View results' : 'Next question'}
              <ArrowRight size={16} aria-hidden="true" />
            </Button>
          )}
        </>
      ) : (
        <>
          <TextArea
            label="Your answer"
            rows={7}
            value={textValue}
            onChange={(event) => setTextValue(event.target.value)}
            placeholder="Answer as you would in a real interview — specific, concrete, and complete. Vague or off-topic answers score poorly."
            hint={`${words} word${words === 1 ? '' : 's'}`}
          />
          <Button
            onClick={goNext}
            disabled={!canProceedText}
            isLoading={isLast && isSubmitting}
            className="w-fit self-end"
          >
            {isLast ? 'Submit assessment' : 'Next question'}
            <ArrowRight size={16} aria-hidden="true" />
          </Button>
        </>
      )}
    </Card>
  )
}

function ScoreVerdictIcon({ isCorrect }) {
  return isCorrect ? (
    <CheckCircle2 size={18} className="shrink-0 text-success" aria-hidden="true" />
  ) : (
    <XCircle size={18} className="shrink-0 text-danger" aria-hidden="true" />
  )
}

function QuestionFeedbackCard({ feedback }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <ScoreVerdictIcon isCorrect={feedback.is_correct} />
          <Badge tone="accent">{typeLabel(feedback.type)}</Badge>
          {feedback.difficulty && (
            <Badge tone={DIFFICULTY_TONE[feedback.difficulty] || 'neutral'}>{feedback.difficulty}</Badge>
          )}
          <Badge tone="neutral">{feedback.category}</Badge>
        </div>
        <span className="text-sm font-semibold text-text-h">{feedback.score}/100</span>
      </div>

      <p className="text-sm font-medium text-text-h">{feedback.question}</p>

      <div className="rounded-md border border-border bg-bg p-3">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text/70">Your answer</p>
        <p className="text-sm text-text">{feedback.answer || <span className="italic text-text/50">No answer submitted</span>}</p>
      </div>

      <div className="rounded-md bg-surface p-3">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">Why this score</p>
        <p className="text-sm text-text-h">{feedback.explanation}</p>
      </div>

      <div className="flex items-start gap-2 rounded-md border border-dashed border-border p-3">
        <Lightbulb size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-text-h">
            {SOFT_QUESTION_TYPES.has(feedback.type) ? 'How to improve' : 'Correct answer'}
          </p>
          <p className="mt-0.5 text-sm text-text">{feedback.correct_answer_or_improvement}</p>
        </div>
      </div>
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
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-text">Overall score</p>
          <SourceBadge source={result.source} />
        </div>
        <div className={clsx('text-5xl font-bold', bandColors.text)}>{result.overall_score}</div>
        <Badge tone={band.tone}>{band.label}</Badge>
        <p className="text-sm text-text">
          {result.correct_count} of {result.total} technical &amp; problem-solving questions correct
        </p>
        {result.source === 'fallback' && (
          <p className="flex items-center gap-1.5 text-xs text-text/70">
            <AlertCircle size={13} aria-hidden="true" /> AI grading was unavailable for this attempt — scores used rule-based checks instead.
          </p>
        )}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="flex flex-col gap-1">
          <p className="text-sm font-medium text-text">Technical &amp; problem-solving score</p>
          <p className="text-2xl font-semibold text-text-h">{result.technical_score}</p>
        </Card>
        <Card className="flex flex-col gap-1">
          <p className="text-sm font-medium text-text">Scenario &amp; behavioral score</p>
          <p className="text-2xl font-semibold text-text-h">{result.soft_score}</p>
        </Card>
      </div>

      {breakdownItems.length > 0 && (
        <Card>
          <h2 className="mb-3 text-base font-semibold text-text-h">Category breakdown</h2>
          <ScoreBreakdownBars items={breakdownItems} caption="Average score per matched skill category." />
        </Card>
      )}

      <div>
        <h2 className="mb-3 text-base font-semibold text-text-h">Question-by-question feedback</h2>
        <div className="flex flex-col gap-4">
          {result.question_feedback.map((feedback) => (
            <QuestionFeedbackCard key={feedback.question_id} feedback={feedback} />
          ))}
        </div>
      </div>

      <Button variant="secondary" onClick={onRetake} className="w-fit">
        <RotateCcw size={16} aria-hidden="true" />
        Retake assessment
      </Button>
    </div>
  )
}

export default function SkillAssessmentPage() {
  const [phase, setPhase] = useState('intro')
  const [questionCount, setQuestionCount] = useState(DEFAULT_QUESTION_COUNT)
  const buildQuery = useSkillAssessmentBuild(questionCount)
  const submitMutation = useSubmitSkillAssessment()
  const [result, setResult] = useState(null)

  const sessionId = useMemo(() => buildQuery.data?.session_id, [buildQuery.data])

  function handleQuestionsComplete(answers) {
    submitMutation.mutate(
      { sessionId, answers },
      {
        onSuccess: (data) => {
          setResult(data)
          setPhase('results')
        },
      }
    )
  }

  function handleRetake() {
    setResult(null)
    setPhase('intro')
    buildQuery.refetch()
  }

  return (
    <div className="flex flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Skill assessment</h1>
        <p className="mt-1 text-sm text-text">
          Interview-level technical, scenario-based, problem-solving, and behavioral questions for your target role.
        </p>
      </div>

      {buildQuery.isLoading && (
        <div className="flex flex-col items-center gap-2 py-16">
          <Spinner label="Building your assessment…" />
          <p className="text-xs text-text/60">
            Generating personalized questions can take up to 20-30 seconds — hang tight.
          </p>
        </div>
      )}

      {buildQuery.isError && <ErrorState message={buildQuery.error.message} onRetry={buildQuery.refetch} />}

      {buildQuery.isSuccess && phase === 'intro' && (
        <IntroPhase
          build={buildQuery.data}
          onBegin={() => setPhase('questions')}
          questionCount={questionCount}
          onQuestionCountChange={setQuestionCount}
        />
      )}

      {buildQuery.isSuccess && phase === 'questions' && (
        <QuestionPhase
          questions={buildQuery.data.questions}
          onComplete={handleQuestionsComplete}
          isSubmitting={submitMutation.isPending}
        />
      )}

      {submitMutation.isError && <p className="text-sm text-danger">{submitMutation.error.message}</p>}

      {phase === 'results' && result && <ResultsPhase result={result} onRetake={handleRetake} />}
    </div>
  )
}
