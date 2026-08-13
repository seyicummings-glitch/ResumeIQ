import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import {
  Sparkles,
  RotateCcw,
  MessageSquare,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  ThumbsUp,
  ListChecks,
  BookOpen,
  Lightbulb,
  LoaderCircle,
  Send,
  X,
  Target,
} from 'lucide-react'
import { useInterviewQuestions, useInterviewChat, useSaveInterviewSession } from '../hooks/useInterviewQuestions'
import { useSpeechVoice } from '../hooks/useSpeechVoice'
import Button, { buttonClasses } from '../components/ui/Button'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import ScoreBadge from '../components/ui/ScoreBadge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import FeatureLimitNotice from '../components/subscription/FeatureLimitNotice'

function FeedbackSection({ icon: Icon, title, items }) {
  if (!items || items.length === 0) return null
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5">
        <Icon size={14} className="text-accent" aria-hidden="true" />
        <p className="text-xs font-semibold uppercase tracking-wide text-text/70">{title}</p>
      </div>
      <ul className="flex flex-col gap-1 text-sm text-text-h">
        {items.map((item, index) => (
          <li key={index}>• {item}</li>
        ))}
      </ul>
    </div>
  )
}

function AssessmentCard({ title, text }) {
  if (!text) return null
  return (
    <div className="rounded-lg bg-surface p-3">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text/70">{title}</p>
      <p className="text-sm text-text-h">{text}</p>
    </div>
  )
}

function SessionReport({ sessionResult }) {
  const { feedback } = sessionResult
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-base font-semibold text-text-h">Interview feedback</h2>
        <Badge tone={feedback.source === 'ai' ? 'accent' : 'neutral'}>
          {feedback.source === 'ai' ? 'AI-generated' : 'Rule-based fallback'}
        </Badge>
        {typeof feedback.overall_score === 'number' ? (
          <ScoreBadge score={feedback.overall_score} className="ml-auto" />
        ) : (
          <Badge tone="neutral" className="ml-auto">
            Not scored
          </Badge>
        )}
      </div>

      <p className="text-sm text-text-h">{feedback.overall_assessment}</p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <AssessmentCard title="Technical performance" text={feedback.technical_performance} />
        <AssessmentCard title="Communication" text={feedback.communication_assessment} />
        <AssessmentCard title="Confidence" text={feedback.confidence_assessment} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FeedbackSection icon={ThumbsUp} title="Strengths" items={feedback.strengths} />
        <FeedbackSection icon={ListChecks} title="Areas to improve" items={feedback.areas_to_improve} />
        <FeedbackSection icon={Target} title="Recommended improvements" items={feedback.recommended_improvements} />
        <FeedbackSection icon={BookOpen} title="Study topics" items={feedback.study_topics} />
        <FeedbackSection icon={Lightbulb} title="Role knowledge tips" items={feedback.role_knowledge_tips} />
      </div>
    </Card>
  )
}

function ModeToggle({ mode, onChange }) {
  return (
    <div className="flex items-center rounded-md border border-border p-0.5">
      <button
        type="button"
        onClick={() => onChange('voice')}
        className={clsx(
          'flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition-colors',
          mode === 'voice' ? 'bg-accent text-accent-contrast' : 'text-text/70 hover:text-text-h'
        )}
      >
        <Mic size={12} aria-hidden="true" />
        Voice
      </button>
      <button
        type="button"
        onClick={() => onChange('text')}
        className={clsx(
          'flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition-colors',
          mode === 'text' ? 'bg-accent text-accent-contrast' : 'text-text/70 hover:text-text-h'
        )}
      >
        <MessageSquare size={12} aria-hidden="true" />
        Text
      </button>
    </div>
  )
}

function ChatLog({ messages, isPending }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, isPending])

  return (
    <Card className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
      {messages.map((message, index) => (
        <div key={index} className={clsx('flex', message.role === 'candidate' ? 'justify-end' : 'justify-start')}>
          <div
            className={clsx(
              'max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed',
              message.role === 'candidate' ? 'bg-accent text-accent-contrast' : 'bg-surface text-text-h'
            )}
          >
            {message.content}
          </div>
        </div>
      ))}
      {isPending && (
        <div className="flex items-center gap-2 text-sm text-text/70">
          <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />
          {messages.length === 0 ? 'Preparing your first question…' : 'Reviewing your answer…'}
        </div>
      )}
      <div ref={endRef} />
    </Card>
  )
}

export default function InterviewPracticePage() {
  const { data, isLoading, isError, error, refetch } = useInterviewQuestions()
  const chat = useInterviewChat()
  const saveSession = useSaveInterviewSession()
  const voice = useSpeechVoice()

  // messages holds the full {role, content} history — needed to keep the AI's own
  // conversation context and for the persisted transcript, but is never rendered as
  // a chat log; only the current turn's feedback/question are shown on screen.
  const [mode, setMode] = useState(() => (voice.recognitionSupported ? 'voice' : 'text'))
  const [messages, setMessages] = useState([])
  const [currentFeedback, setCurrentFeedback] = useState('')
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [answerSource, setAnswerSource] = useState(null)
  const [interimTranscript, setInterimTranscript] = useState('')
  const [textAnswer, setTextAnswer] = useState('')
  const [started, setStarted] = useState(false)
  const [done, setDone] = useState(false)
  const [chatError, setChatError] = useState(null)
  const [limitDetail, setLimitDetail] = useState(null)
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(true)
  const [sessionResult, setSessionResult] = useState(null)

  function speakIfEnabled(text) {
    if (mode === 'voice' && voiceOutputEnabled) voice.speak(text)
  }

  function switchMode(nextMode) {
    if (nextMode === mode) return
    voice.stopListening()
    voice.stopSpeaking()
    setInterimTranscript('')
    setMode(nextMode)
  }

  async function finishSession(finalMessages) {
    try {
      const result = await saveSession.mutateAsync({
        transcript: finalMessages.map(({ role, content }) => ({ role, content })),
        audioBlob: null,
        mode,
      })
      setSessionResult(result)
    } catch (err) {
      setChatError(err.message)
    }
  }

  async function startInterview() {
    setLimitDetail(null)
    setChatError(null)
    setMessages([])
    setCurrentFeedback('')
    setCurrentQuestion('')
    setInterimTranscript('')
    setTextAnswer('')
    setSessionResult(null)
    voice.stopSpeaking()

    try {
      const result = await chat.mutateAsync({ conversation: [], preferredLanguage: navigator.language, mode })
      setStarted(true)
      setDone(false)
      const spoken = result.feedback ? `${result.feedback} ${result.question}` : result.question
      const initialMessages = [{ role: 'interviewer', content: spoken }]
      setMessages(initialMessages)
      setCurrentFeedback(result.feedback)
      setCurrentQuestion(result.question)
      setAnswerSource(result.source)
      setDone(result.done)
      speakIfEnabled(spoken)
      if (result.done) await finishSession(initialMessages)
    } catch (err) {
      if (err.status === 402) {
        setLimitDetail(err.detail)
      } else {
        setStarted(true)
        setChatError(err.message)
      }
    }
  }

  async function submitAnswer(text) {
    const trimmed = text.trim()
    if (!trimmed || chat.isPending || done) return

    setInterimTranscript('')
    const nextMessages = [...messages, { role: 'candidate', content: trimmed }]
    setMessages(nextMessages)
    setChatError(null)

    try {
      const result = await chat.mutateAsync({
        conversation: nextMessages.map(({ role, content }) => ({ role, content })),
      })
      const spoken = result.feedback ? `${result.feedback} ${result.question}` : result.question
      const updatedMessages = [...nextMessages, { role: 'interviewer', content: spoken }]
      setMessages(updatedMessages)
      setCurrentFeedback(result.feedback)
      setCurrentQuestion(result.question)
      setAnswerSource(result.source)
      setDone(result.done)
      speakIfEnabled(spoken)
      if (result.done) await finishSession(updatedMessages)
    } catch (err) {
      setChatError(err.message)
    }
  }

  function handleTextSubmit(event) {
    event.preventDefault()
    const value = textAnswer
    setTextAnswer('')
    submitAnswer(value)
  }

  // Voice answers are never auto-submitted — the transcript lands in the same editable
  // box text mode uses, so the candidate can confirm or fix it (misheard words, a cut-off
  // sentence) before it's actually sent. This also means a genuinely-empty transcript can
  // no longer read as a confusing "the AI ignored my answer" — it either becomes reviewable
  // text, or a clear "didn't catch that" message shows (see useSpeechVoice's onend/onerror).
  function handleVoiceFinalTranscript(transcript) {
    setInterimTranscript('')
    setTextAnswer(transcript)
  }

  function toggleMic() {
    if (voice.isListening) {
      voice.stopListening()
      return
    }
    voice.stopSpeaking()
    setInterimTranscript('')
    voice.startListening(setInterimTranscript, handleVoiceFinalTranscript)
  }

  function toggleVoiceOutput() {
    if (voiceOutputEnabled) voice.stopSpeaking()
    setVoiceOutputEnabled((value) => !value)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  if (!data.has_analysis) {
    return (
      <div className="flex flex-col gap-6 py-8">
        <div>
          <h1 className="text-2xl font-semibold text-text-h">Interview practice</h1>
          <p className="mt-1 text-sm text-text">A live voice mock interview, tailored to your resume and the job you're applying for.</p>
        </div>
        <EmptyState
          icon={MessageSquare}
          title="Save an analysis first"
          description="The mock interview is built from your specific resume and a job description you've matched it against — save one from your dashboard to unlock it."
          action={
            <Link to="/dashboard" className={buttonClasses()}>
              Go to dashboard
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col gap-4 py-8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-text-h">Interview practice</h1>
          <p className="mt-1 text-sm text-text">
            {mode === 'voice' ? 'Live voice interview' : 'Text chat interview'} for{' '}
            <span className="font-medium text-text-h">{data.jd_title || 'your target role'}</span>
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {voice.recognitionSupported && <ModeToggle mode={mode} onChange={switchMode} />}
          {mode === 'voice' && voice.synthesisSupported && (
            <Button
              variant="secondary"
              size="sm"
              onClick={toggleVoiceOutput}
              title={voiceOutputEnabled ? 'Mute the interviewer’s voice' : 'Unmute the interviewer’s voice'}
            >
              {voiceOutputEnabled ? <Volume2 size={14} aria-hidden="true" /> : <VolumeX size={14} aria-hidden="true" />}
            </Button>
          )}
          {started && (
            <Button variant="secondary" size="sm" onClick={startInterview}>
              <RotateCcw size={14} aria-hidden="true" />
              Restart
            </Button>
          )}
        </div>
      </div>

      {!started ? (
        <Card className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
          {limitDetail && (
            <div className="w-full max-w-md text-left">
              <FeatureLimitNotice detail={limitDetail} onDismiss={() => setLimitDetail(null)} />
            </div>
          )}
          <div
            className="flex h-14 w-14 items-center justify-center rounded-full text-white"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}
          >
            <Sparkles size={24} aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-h">Ready when you are</h2>
            <p className="mx-auto mt-1 max-w-sm text-sm text-text">
              You'll get one question at a time, just like talking with a real interviewer — answer by typing or,
              if your browser supports it, by speaking into your mic (you'll get to review and edit the
              transcript before it's sent), and switch between the two whenever you like. After each answer
              you'll get direct feedback on it, and a full report when you finish.
            </p>
          </div>
          <Button onClick={startInterview} isLoading={chat.isPending}>
            Start interview
          </Button>
        </Card>
      ) : mode === 'text' ? (
        <>
          <ChatLog messages={messages} isPending={chat.isPending} />

          {done && !sessionResult && (
            <div className="flex items-center justify-center gap-2 text-xs text-text/70">
              <LoaderCircle size={13} className="animate-spin" aria-hidden="true" />
              Generating your feedback report…
            </div>
          )}
          {done && sessionResult && (
            <div className="flex justify-center">
              <Badge tone="success">Interview complete</Badge>
            </div>
          )}

          {chatError && <p className="text-sm text-danger">{chatError}</p>}

          {answerSource === 'fallback' && (
            <p className="text-xs text-text/70">
              Running in scripted practice mode (AI interviewer unavailable) — you're still working through real,
              personalized questions, just without per-answer AI feedback.
            </p>
          )}

          {sessionResult && <SessionReport sessionResult={sessionResult} />}

          {!done && (
            <form onSubmit={handleTextSubmit} className="flex items-center gap-2 rounded-xl border border-border bg-surface p-2">
              <input
                type="text"
                value={textAnswer}
                onChange={(event) => setTextAnswer(event.target.value)}
                placeholder="Type your answer…"
                disabled={chat.isPending}
                autoFocus
                className="flex-1 bg-transparent px-2 py-2 text-sm text-text-h placeholder:text-text/50 focus:outline-none disabled:opacity-50"
              />
              <Button type="submit" size="md" disabled={!textAnswer.trim() || chat.isPending} title="Send">
                <Send size={16} aria-hidden="true" />
              </Button>
            </form>
          )}
        </>
      ) : (
        <>
          <Card className="flex flex-1 flex-col justify-center gap-4 overflow-y-auto p-6">
            {chat.isPending ? (
              <div className="flex flex-1 items-center justify-center gap-2 text-sm text-text/70">
                <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />
                {messages.length === 0 ? 'Preparing your first question…' : 'Reviewing your answer…'}
              </div>
            ) : (
              <>
                {currentFeedback && (
                  <div className="rounded-lg bg-surface p-4">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
                      Feedback on your last answer
                    </p>
                    <p className="text-sm text-text-h">{currentFeedback}</p>
                  </div>
                )}
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text/70">
                    {done ? 'Wrap-up' : 'Question'}
                  </p>
                  <p className="text-lg font-medium leading-relaxed text-text-h">{currentQuestion}</p>
                </div>
                {interimTranscript && (
                  <div className="rounded-lg border border-dashed border-border p-3">
                    <p className="mb-1 text-xs text-text/60">You're saying…</p>
                    <p className="text-sm text-text-h">{interimTranscript}</p>
                  </div>
                )}
              </>
            )}

            {done && !sessionResult && (
              <div className="flex items-center justify-center gap-2 pt-2 text-xs text-text/70">
                <LoaderCircle size={13} className="animate-spin" aria-hidden="true" />
                Generating your feedback report…
              </div>
            )}
            {done && sessionResult && (
              <div className="flex justify-center pt-2">
                <Badge tone="success">Interview complete</Badge>
              </div>
            )}
          </Card>

          {chatError && <p className="text-sm text-danger">{chatError}</p>}

          {answerSource === 'fallback' && (
            <p className="text-xs text-text/70">
              Running in scripted practice mode (AI interviewer unavailable) — you're still working through real,
              personalized questions, just without per-answer AI feedback.
            </p>
          )}

          {sessionResult && <SessionReport sessionResult={sessionResult} />}

          {!done && (
            <div className="flex flex-col items-center gap-2 rounded-xl border border-border bg-surface p-4">
              {(voice.isSpeaking || voice.isListening) && (
                <p className="flex items-center gap-1.5 text-xs text-accent">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                  {voice.isSpeaking ? 'Interviewer is speaking…' : 'Listening…'}
                </p>
              )}
              <Button
                type="button"
                size="lg"
                variant={voice.isListening ? 'primary' : 'secondary'}
                onClick={toggleMic}
                disabled={chat.isPending || voice.isSpeaking}
                className="h-16 w-16 !rounded-full"
                title={voice.isListening ? 'Stop and review' : 'Tap to answer'}
              >
                {voice.isListening ? <MicOff size={22} aria-hidden="true" /> : <Mic size={22} aria-hidden="true" />}
              </Button>
              <p className="text-xs text-text/60">
                {voice.isListening ? 'Tap again to stop and review your answer' : 'Tap to answer by voice'}
              </p>
              {voice.recognitionError && <p className="text-center text-xs text-danger">{voice.recognitionError}</p>}

              {textAnswer && !voice.isListening && (
                <form onSubmit={handleTextSubmit} className="flex w-full items-center gap-2 rounded-lg border border-border bg-bg p-2">
                  <input
                    type="text"
                    value={textAnswer}
                    onChange={(event) => setTextAnswer(event.target.value)}
                    placeholder="Review or edit your transcribed answer…"
                    disabled={chat.isPending}
                    autoFocus
                    className="flex-1 bg-transparent px-2 py-2 text-sm text-text-h placeholder:text-text/50 focus:outline-none disabled:opacity-50"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="md"
                    onClick={() => setTextAnswer('')}
                    disabled={chat.isPending}
                    title="Discard this answer"
                  >
                    <X size={16} aria-hidden="true" />
                  </Button>
                  <Button type="submit" size="md" disabled={!textAnswer.trim() || chat.isPending} title="Send">
                    <Send size={16} aria-hidden="true" />
                  </Button>
                </form>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
