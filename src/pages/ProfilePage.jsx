import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { UserRound, KeyRound } from 'lucide-react'
import clsx from 'clsx'
import { useProfile, useUpdateProfile, useChangePassword } from '../hooks/useProfile'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import Card from '../components/ui/Card'
import Input from '../components/ui/Input'
import PhoneInput from '../components/ui/PhoneInput'
import TextArea from '../components/ui/TextArea'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import { Tabs } from '../components/ui/Tabs'
import { useToast } from '../components/ui/Toast'

const INDUSTRIES = [
  'Software Engineering',
  'Finance & Banking',
  'Healthcare',
  'Marketing',
  'Business & Operations',
  'Data Science',
  'Design (UX/UI)',
  'Sales',
]

const EXPERIENCE_LEVELS = [
  { id: 'entry', label: 'Entry', sub: '0-2 yrs' },
  { id: 'mid', label: 'Mid', sub: '3-5 yrs' },
  { id: 'senior', label: 'Senior', sub: '6-10 yrs' },
  { id: 'exec', label: 'Exec', sub: '10+ yrs' },
]

const profileSchema = z.object({
  fullName: z.string().optional(),
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  phone: z.string().optional(),
  location: z.string().optional(),
  targetRole: z.string().optional(),
  industry: z.string().optional(),
  linkedinUrl: z.string().optional(),
  githubUrl: z.string().optional(),
  portfolioUrl: z.string().optional(),
  careerGoals: z.string().optional(),
})

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: z.string().min(8, 'Password must be 8 characters').max(8, 'Password must be 8 characters'),
    confirmNewPassword: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((data) => data.newPassword === data.confirmNewPassword, {
    message: "Passwords don't match",
    path: ['confirmNewPassword'],
  })

function SectionHeader({ icon: Icon, title, description }) {
  return (
    <div className="mb-5 flex items-start gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
        <Icon size={17} aria-hidden="true" />
      </div>
      <div>
        <h2 className="text-sm font-semibold text-text-h">{title}</h2>
        {description && <p className="mt-0.5 text-xs text-text">{description}</p>}
      </div>
    </div>
  )
}

function ProfileTab({ profile }) {
  const updateProfile = useUpdateProfile()
  const { refreshUser } = useAuth()
  const { showToast } = useToast()
  const [formError, setFormError] = useState(null)
  const [experienceLevel, setExperienceLevel] = useState(profile.experience_level || 'mid')

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors, isDirty },
  } = useForm({
    resolver: zodResolver(profileSchema),
    values: {
      fullName: profile.full_name || '',
      email: profile.email,
      phone: profile.phone || '',
      location: profile.location || '',
      targetRole: profile.target_role || '',
      industry: profile.industry || '',
      linkedinUrl: profile.linkedin_url || '',
      githubUrl: profile.github_url || '',
      portfolioUrl: profile.portfolio_url || '',
      careerGoals: profile.career_goals || '',
    },
  })

  async function onSubmit(values) {
    setFormError(null)
    try {
      await updateProfile.mutateAsync({ ...values, experienceLevel })
      await refreshUser()
      showToast('Profile updated.', { tone: 'success' })
      reset(values)
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        setFormError('That email is already registered to another account.')
      } else {
        setFormError(error.message)
      }
    }
  }

  return (
    <Card className="p-6">
      <SectionHeader icon={UserRound} title="Account details" description="Your info, links, and career goals." />
      {formError && (
        <p role="alert" className="mb-4 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
          {formError}
        </p>
      )}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Full name" autoComplete="name" {...register('fullName')} />
          <Input label="Email" type="email" autoComplete="email" required error={errors.email?.message} {...register('email')} />
          <Controller
            name="phone"
            control={control}
            render={({ field }) => (
              <PhoneInput label="Phone" value={field.value} onChange={field.onChange} placeholder="555 000 0000" />
            )}
          />
          <Input label="Location" placeholder="San Francisco, CA" {...register('location')} />
          <Input label="Target role" placeholder="Senior Software Engineer" {...register('targetRole')} />
          <div>
            <Input
              label="Industry"
              list="industry-options"
              placeholder="Select or type your own…"
              {...register('industry')}
            />
            <datalist id="industry-options">
              {INDUSTRIES.map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
          </div>
          <Input label="LinkedIn" placeholder="linkedin.com/in/username" {...register('linkedinUrl')} />
          <Input label="GitHub" placeholder="github.com/username" {...register('githubUrl')} />
        </div>

        <Input label="Portfolio" placeholder="https://yourportfolio.com" {...register('portfolioUrl')} />

        <div>
          <p className="mb-1.5 text-sm font-medium text-text-h">Experience level</p>
          <div className="grid grid-cols-4 gap-2">
            {EXPERIENCE_LEVELS.map(({ id, label, sub }) => (
              <button
                key={id}
                type="button"
                onClick={() => setExperienceLevel(id)}
                className={clsx(
                  'rounded-md border px-2 py-2 text-center transition-colors',
                  experienceLevel === id ? 'border-accent bg-accent/10 text-accent' : 'border-border text-text hover:bg-surface'
                )}
              >
                <div className="text-xs font-semibold">{label}</div>
                <div className="font-mono text-[10px] opacity-70">{sub}</div>
              </button>
            ))}
          </div>
        </div>

        <TextArea
          label="Career goals"
          rows={3}
          placeholder="Describe your career goals and what roles you're targeting…"
          {...register('careerGoals')}
        />

        <div>
          <Button type="submit" isLoading={updateProfile.isPending} disabled={!isDirty}>
            Save changes
          </Button>
        </div>
      </form>
    </Card>
  )
}

function SecurityTab() {
  const changePassword = useChangePassword()
  const { showToast } = useToast()
  const [formError, setFormError] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(passwordSchema) })

  async function onSubmit(values) {
    setFormError(null)
    try {
      await changePassword.mutateAsync({ currentPassword: values.currentPassword, newPassword: values.newPassword })
      showToast('Password updated.', { tone: 'success' })
      reset()
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError('Current password is incorrect.')
      } else {
        setFormError(error.message)
      }
    }
  }

  return (
    <Card className="p-6">
      <SectionHeader icon={KeyRound} title="Password" description="Update the password used to sign in." />
      {formError && (
        <p role="alert" className="mb-4 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
          {formError}
        </p>
      )}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input
          label="Current password"
          type="password"
          autoComplete="current-password"
          required
          error={errors.currentPassword?.message}
          {...register('currentPassword')}
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            required
            maxLength={8}
            hint="Must be 8 characters"
            error={errors.newPassword?.message}
            {...register('newPassword')}
          />
          <Input
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            required
            maxLength={8}
            error={errors.confirmNewPassword?.message}
            {...register('confirmNewPassword')}
          />
        </div>
        <div>
          <Button type="submit" isLoading={isSubmitting}>
            Update password
          </Button>
        </div>
      </form>
    </Card>
  )
}

export default function ProfilePage() {
  const { data: profile, isLoading, isError, error, refetch } = useProfile()
  const [activeTab, setActiveTab] = useState('profile')

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading your profile…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  const displayName = profile.full_name?.trim() || profile.email
  const initial = displayName[0].toUpperCase()

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 py-8">
      <Card className="flex flex-col items-center gap-4 p-8 text-center sm:flex-row sm:items-center sm:text-left">
        <div
          className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-xl font-bold text-white"
          style={{ background: 'linear-gradient(135deg, #4f46e5, var(--accent-2))' }}
          aria-hidden="true"
        >
          {initial}
        </div>
        <div className="flex-1">
          <div className="flex flex-col items-center gap-2 sm:flex-row">
            <h1 className="text-xl font-semibold text-text-h">{displayName}</h1>
            <Badge tone={profile.role === 'admin' ? 'accent' : 'neutral'}>{profile.role}</Badge>
          </div>
          <p className="mt-1 text-sm text-text">{profile.email}</p>
          <p className="mt-1 text-xs text-text/70">
            Member since {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(profile.created_at))}
          </p>
        </div>
      </Card>

      <Tabs
        tabs={[
          { id: 'profile', label: 'Profile' },
          { id: 'security', label: 'Security' },
        ]}
        activeId={activeTab}
        onChange={setActiveTab}
      >
        {activeTab === 'profile' && <ProfileTab profile={profile} />}
        {activeTab === 'security' && <SecurityTab />}
      </Tabs>
    </div>
  )
}
