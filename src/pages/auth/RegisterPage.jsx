import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Copy, Check } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'
import { passwordSchema, PASSWORD_REQUIREMENTS_TEXT } from '../../lib/passwordValidation'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import PasswordInput from '../../components/ui/PasswordInput'
import Button from '../../components/ui/Button'

const schema = z
  .object({
    fullName: z.string().optional(),
    email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  })

export default function RegisterPage() {
  const { register: registerUser } = useAuth()
  const [formError, setFormError] = useState(null)
  // Set on success — new accounts must verify their email before they can log
  // in, so this replaces the form with a "check your inbox" state instead of
  // navigating straight to the dashboard.
  const [result, setResult] = useState(null)
  const [copied, setCopied] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  async function onSubmit(values) {
    setFormError(null)
    try {
      const response = await registerUser(values)
      setResult(response)
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        setFormError('That email is already registered. Try logging in instead.')
      } else {
        setFormError(error.message)
      }
    }
  }

  async function copyToken() {
    if (!result?.verification_token) return
    await navigator.clipboard.writeText(result.verification_token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-text-h">Create your account</h1>
        <p className="mt-1 text-sm text-text">Start scoring and matching your resume in minutes.</p>
      </div>

      <Card>
        {formError && (
          <p role="alert" className="mb-4 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}

        {result ? (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-text-h">{result.message}</p>
            {result.verification_token ? (
              <>
                <p className="rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning">
                  Development mode: this app doesn't send real emails yet, so your verification code is shown here
                  directly. Normally it would only be emailed to you.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 truncate rounded-lg border border-border bg-bg px-3 py-2 text-xs text-text-h">
                    {result.verification_token}
                  </code>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={copyToken}
                    aria-label="Copy verification code"
                  >
                    {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
                  </Button>
                </div>
                <Link
                  to={`/verify-email?token=${encodeURIComponent(result.verification_token)}`}
                  className="text-center text-sm font-medium text-accent hover:underline"
                >
                  Continue to verify email
                </Link>
              </>
            ) : (
              <p className="text-sm text-text">
                Click the link in that email, then come back and log in.
              </p>
            )}
            <Link to="/login" className="text-center text-sm font-medium text-accent hover:underline">
              Go to login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
            <Input label="Full name" autoComplete="name" {...register('fullName')} />
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              required
              error={errors.email?.message}
              {...register('email')}
            />
            <PasswordInput
              label="Password"
              autoComplete="new-password"
              required
              maxLength={20}
              hint={PASSWORD_REQUIREMENTS_TEXT}
              error={errors.password?.message}
              {...register('password')}
            />
            <PasswordInput
              label="Confirm password"
              autoComplete="new-password"
              required
              error={errors.confirmPassword?.message}
              {...register('confirmPassword')}
            />
            <Button type="submit" isLoading={isSubmitting} className="w-full">
              Create account
            </Button>
          </form>
        )}
      </Card>

      <p className="text-center text-sm text-text">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent hover:underline">
          Log in
        </Link>
      </p>
    </div>
  )
}
