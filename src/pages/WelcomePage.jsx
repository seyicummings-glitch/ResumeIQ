import { Link } from 'react-router-dom'
import { FileSearch, Target, GitFork, Sparkles } from 'lucide-react'
import { buttonClasses } from '../components/ui/Button'
import Card from '../components/ui/Card'
import { useAuth } from '../auth/AuthContext'

const FEATURES = [
  {
    icon: FileSearch,
    title: 'ATS compatibility score',
    description: 'Upload your resume and see how well real applicant-tracking systems would parse it, with concrete fixes.',
  },
  {
    icon: Target,
    title: 'Resume-to-job matching',
    description: 'Compare your resume against any job description and get a scored breakdown of skills, experience, and qualifications.',
  },
  {
    icon: GitFork,
    title: 'GitHub-aware recommendations',
    description: 'Optionally factor your GitHub activity in as a secondary signal alongside your resume.',
  },
  {
    icon: Sparkles,
    title: 'AI-assisted suggestions',
    description: 'Get specific, actionable improvement suggestions for your resume, tailored to a target role.',
  },
]

export default function WelcomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="flex flex-col gap-16 py-8">
      <section className="flex flex-col items-center gap-4 text-center">
        <h1 className="max-w-2xl text-4xl font-semibold text-text-h sm:text-5xl">
          Know exactly how your resume stacks up
        </h1>
        <p className="max-w-xl text-lg text-text">
          ResumeIQ scores your resume, matches it against job descriptions, and tells you precisely what to improve —
          no guesswork.
        </p>
        <div className="mt-2 flex gap-3">
          {isAuthenticated ? (
            <Link to="/dashboard" className={buttonClasses({ size: 'lg' })}>
              Go to dashboard
            </Link>
          ) : (
            <>
              <Link to="/register" className={buttonClasses({ size: 'lg' })}>
                Get started
              </Link>
              <Link to="/login" className={buttonClasses({ variant: 'secondary', size: 'lg' })}>
                Log in
              </Link>
            </>
          )}
        </div>
      </section>

      <section aria-label="Features" className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {FEATURES.map((feature) => (
          <Card key={feature.title} className="flex flex-col gap-2">
            <feature.icon size={24} className="text-accent" aria-hidden="true" />
            <h2 className="text-base font-semibold text-text-h">{feature.title}</h2>
            <p className="text-sm text-text">{feature.description}</p>
          </Card>
        ))}
      </section>
    </div>
  )
}
