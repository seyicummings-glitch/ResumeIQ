import { Link } from 'react-router-dom'
import {
  FileSearch,
  Target,
  Sparkles,
  Brain,
  MessageSquare,
  Map,
  GitCompare,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react'
import { buttonClasses } from '../components/ui/Button'
import { useAuth } from '../auth/AuthContext'

const FEATURES = [
  {
    icon: FileSearch,
    title: 'ATS scoring',
    description: 'See exactly how real applicant-tracking systems would parse your resume, with concrete fixes.',
    color: '#2563eb',
  },
  {
    icon: Target,
    title: 'Resume-to-job matching',
    description: 'Score your resume against any job description — skills, experience, and qualifications, weighted.',
    color: '#06b6d4',
  },
  {
    icon: Brain,
    title: 'Skill assessment',
    description: 'A quiz built from your resume’s skills and gaps, with per-category scoring.',
    color: '#8b5cf6',
  },
  {
    icon: MessageSquare,
    title: 'Interview practice',
    description: 'A live mock interview tailored to your resume and the job you’re applying for.',
    color: '#10b981',
  },
  {
    icon: Map,
    title: 'Learning roadmap',
    description: 'A phased plan of real resources to close your specific skill gaps, with progress tracking.',
    color: '#f59e0b',
  },
  {
    icon: GitCompare,
    title: 'Version history',
    description: 'Track every resume version you save and compare scores side by side as you improve.',
    color: '#ef4444',
  },
]

const STEPS = [
  { n: '01', title: 'Upload your resume', description: 'PDF, DOCX, or TXT — we extract and score it automatically.' },
  { n: '02', title: 'Add a job description', description: 'Paste text, upload a file, or link a posting.' },
  { n: '03', title: 'Save your analysis', description: 'Get a match score, skill gaps, and AI-assisted suggestions.' },
  { n: '04', title: 'Improve and track', description: 'Practice interviews, follow your roadmap, and watch your scores climb.' },
]

const BADGES = ['Rule-based scoring, always on', 'AI-assisted suggestions', 'Real ATS parsing', 'Free to get started']

export default function WelcomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden px-4 py-20 text-center sm:py-24">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-96 w-[48rem] -translate-x-1/2 opacity-40"
          style={{ background: 'radial-gradient(ellipse, var(--accent) 0%, transparent 70%)' }}
          aria-hidden="true"
        />
        <div className="relative mx-auto flex max-w-2xl flex-col items-center gap-5">
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-3.5 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
            <span className="font-mono text-xs text-accent">AI-assisted · Real ATS parsing · No guesswork</span>
          </div>

          <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-text-h sm:text-6xl">
            Land the interview.
            <br />
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: 'linear-gradient(90deg, var(--accent), var(--accent-2))' }}
            >
              Know exactly why you didn't.
            </span>
          </h1>

          <p className="max-w-xl text-lg leading-relaxed text-text">
            Upload your resume, paste a job description, and get an ATS compatibility score, skill gap analysis, and
            AI-assisted suggestions — plus a live mock interview and a personalized learning roadmap.
          </p>

          <div className="mt-2 flex flex-wrap justify-center gap-3">
            {isAuthenticated ? (
              <Link to="/dashboard" className={buttonClasses({ size: 'lg' })}>
                <Sparkles size={16} aria-hidden="true" /> Go to dashboard
              </Link>
            ) : (
              <>
                <Link to="/register" className={buttonClasses({ size: 'lg' })}>
                  <Sparkles size={16} aria-hidden="true" /> Analyze my resume free <ArrowRight size={14} aria-hidden="true" />
                </Link>
                <Link to="/login" className={buttonClasses({ variant: 'secondary', size: 'lg' })}>
                  Log in
                </Link>
              </>
            )}
          </div>

          <p className="font-mono text-xs text-text/60">No credit card required · Your data stays on your account</p>
        </div>
      </section>

      {/* Badges row */}
      <section className="border-y border-border px-4 py-6">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-2">
          {BADGES.map((label) => (
            <span key={label} className="rounded-full border border-border px-3 py-1 text-xs text-text">
              {label}
            </span>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <span className="font-mono text-xs uppercase tracking-widest text-text/60">Features</span>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-text-h sm:text-4xl">
              Everything your job search needs
            </h2>
          </div>
          <div aria-label="Features" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl border border-border bg-surface p-5 transition-colors hover:border-accent/40"
              >
                <div
                  className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg"
                  style={{ background: `${feature.color}1a` }}
                >
                  <feature.icon size={18} style={{ color: feature.color }} aria-hidden="true" />
                </div>
                <h3 className="text-sm font-semibold text-text-h">{feature.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-text">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border px-4 py-20">
        <div className="mx-auto max-w-4xl">
          <div className="mb-12 text-center">
            <span className="font-mono text-xs uppercase tracking-widest text-text/60">How it works</span>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-text-h sm:text-4xl">
              From upload to insights in 4 steps
            </h2>
          </div>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step) => (
              <div key={step.n}>
                <div className="font-mono text-xs font-bold text-accent">{step.n}</div>
                <h3 className="mt-2 text-sm font-semibold text-text-h">{step.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-text">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border bg-accent/[0.04] px-4 py-20 text-center">
        <div className="mx-auto flex max-w-xl flex-col items-center gap-4">
          <div className="flex items-center gap-2">
            <ShieldCheck size={14} className="text-success" aria-hidden="true" />
            <span className="font-mono text-xs text-success">Your resume data is private to your account</span>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-text-h sm:text-3xl">
            Ready to optimize your resume?
          </h2>
          {!isAuthenticated && (
            <Link to="/register" className={buttonClasses({ size: 'lg' })}>
              <Sparkles size={16} aria-hidden="true" /> Get started — it's free <ArrowRight size={14} aria-hidden="true" />
            </Link>
          )}
        </div>
      </section>
    </div>
  )
}
