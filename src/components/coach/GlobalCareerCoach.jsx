import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import { MessageCircle, Sparkles, X, Send, LoaderCircle } from 'lucide-react'
import { useCareerCoachContext } from '../../coach/CareerCoachContext'
import { useCareerCoach } from '../../hooks/useCareerCoach'
import Button from '../ui/Button'

/**
 * The one persistent AI assistant available from every authenticated page — mounted once in
 * AppShell rather than per-page. Any page can call useCareerCoachContext().openCoach(topic) to
 * open it, optionally scoped to something specific (e.g. a Learning Roadmap topic); general
 * questions work from anywhere with no topic at all. Conversation survives navigation via
 * CareerCoachContext, so switching pages mid-conversation doesn't lose it.
 */
export default function GlobalCareerCoach() {
  const { state, updateState, openCoach, closeCoach, hydrated } = useCareerCoachContext()
  const { open, messages, topic, error } = state
  const coachChat = useCareerCoach()
  const [input, setInput] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, coachChat.isPending])

  async function handleSend(event) {
    event.preventDefault()
    const text = input.trim()
    if (!text || coachChat.isPending) return
    setInput('')

    const nextMessages = [...messages, { role: 'user', content: text }]
    updateState({ messages: nextMessages, error: null })

    try {
      const result = await coachChat.mutateAsync({ conversation: nextMessages, topicKey: topic?.topic_key })
      updateState({ messages: [...nextMessages, { role: 'coach', content: result.reply, source: result.source }] })
    } catch (err) {
      updateState({ error: err.message })
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => openCoach()}
        aria-label="Open AI Career Coach"
        className="fixed bottom-4 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full text-white shadow-lg transition-transform hover:scale-105"
        style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}
      >
        <MessageCircle size={22} aria-hidden="true" />
      </button>
    )
  }

  return (
    <div className="fixed bottom-20 right-4 z-40 flex h-[32rem] w-[22rem] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-xl border border-border bg-bg shadow-xl sm:bottom-24">
      <div className="flex items-center justify-between gap-2 border-b border-border bg-surface px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <Sparkles size={16} className="shrink-0 text-accent" aria-hidden="true" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-text-h">AI Career Coach</p>
            {topic && <p className="truncate text-xs text-text/60">Discussing: {topic.title}</p>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {topic && (
            <Button variant="ghost" size="sm" onClick={() => updateState({ topic: null })} title="Stop focusing on this topic">
              Clear focus
            </Button>
          )}
          <button
            type="button"
            onClick={closeCoach}
            aria-label="Close AI Career Coach"
            className="rounded-md p-1.5 text-text hover:bg-border/40"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div ref={scrollRef} className="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
        {!hydrated && (
          <div className="flex items-center gap-2 text-xs text-text/60">
            <LoaderCircle size={14} className="animate-spin" aria-hidden="true" /> Loading your conversation…
          </div>
        )}
        {hydrated && messages.length === 0 && (
          <p className="text-sm text-text/70">
            Ask me anything — explain a concept, review your resume or code, get guidance on what to do next, or
            just ask what your last score meant. I already know your target role, your latest analysis, and your
            progress across the platform.
          </p>
        )}
        {messages.map((message, index) => (
          <div key={index} className={clsx('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div
              className={clsx(
                'max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm leading-relaxed',
                message.role === 'user' ? 'bg-accent text-accent-contrast' : 'bg-surface text-text-h'
              )}
            >
              {message.content}
            </div>
          </div>
        ))}
        {coachChat.isPending && (
          <div className="flex items-center gap-2 text-xs text-text/60">
            <LoaderCircle size={14} className="animate-spin" aria-hidden="true" /> Thinking…
          </div>
        )}
      </div>

      {error && <p className="px-3 pb-1 text-xs text-danger">{error}</p>}

      <form onSubmit={handleSend} className="flex items-end gap-2 border-t border-border p-2">
        <textarea
          rows={1}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) handleSend(event)
          }}
          placeholder="Ask the coach…"
          disabled={coachChat.isPending}
          className="flex-1 resize-none rounded-md border border-border bg-surface px-2.5 py-2 text-sm text-text-h placeholder:text-text/50 focus:border-accent focus:outline-none disabled:opacity-50"
        />
        <Button type="submit" size="md" disabled={!input.trim() || coachChat.isPending} title="Send">
          <Send size={15} aria-hidden="true" />
        </Button>
      </form>
    </div>
  )
}
