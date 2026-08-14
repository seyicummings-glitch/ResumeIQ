import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'
import { resendVerification } from '../../api/auth'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import PasswordInput from '../../components/ui/PasswordInput'
import Button from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [searchParams] = useSearchParams()
  const [formError, setFormError] = useState(null)
  // Set when login 403s with the structured "email_not_verified" detail (see
  // app/routes/auth.py's login()) so we can offer a resend action instead of
  // just showing the error text.
  const [needsVerification, setNeedsVerification] = useState(false)
  const [resendState, setResendState] = useState('idle') // 'idle' | 'sending' | 'sent'

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  useEffect(() => {
    if (searchParams.get('sessionExpired')) {
      setFormError('Your session expired. Please log in again.')
    }
  }, [searchParams])

  async function onSubmit(values) {
    setFormError(null)
    setNeedsVerification(false)
    setResendState('idle')
    try {
      const me = await login(values)
      showToast('Logged in successfully.', { tone: 'success' })
      const redirect = searchParams.get('redirect')
      // Admins land on the Admin Dashboard by default — "Switch to User
      // View" is there if they want the regular customer experience instead.
      // An explicit redirect (e.g. bounced here from a protected page) still
      // wins over that default.
      const destination = redirect || (me.role === 'admin' ? '/admin' : '/dashboard')
      navigate(destination, { replace: true })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError('Incorrect email or password.')
      } else if (error instanceof ApiError && error.status === 403 && error.detail?.code === 'email_not_verified') {
        setFormError(error.message)
        setNeedsVerification(true)
      } else {
        setFormError(error.message)
      }
    }
  }

  async function handleResend() {
    const email = getValues('email')
    if (!email) return
    setResendState('sending')
    try {
      await resendVerification(email)
      setResendState('sent')
    } catch {
      setResendState('idle')
    }
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-text-h">Log in</h1>
        <p className="mt-1 text-sm text-text">Welcome back — enter your details to continue.</p>
      </div>

      <Card>
        {formError && (
          <div className="mb-4 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
            <p role="alert">{formError}</p>
            {needsVerification && (
              <button
                type="button"
                onClick={handleResend}
                disabled={resendState === 'sending' || resendState === 'sent'}
                className="mt-1 font-medium underline disabled:no-underline disabled:opacity-70"
              >
                {resendState === 'sent'
                  ? 'Verification email sent — check your inbox.'
                  : resendState === 'sending'
                    ? 'Sending…'
                    : 'Resend verification email'}
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
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
            autoComplete="current-password"
            required
            error={errors.password?.message}
            {...register('password')}
          />
          <div className="flex justify-end">
            <Link to="/forgot-password" className="text-sm text-accent hover:underline">
              Forgot password?
            </Link>
          </div>
          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Log in
          </Button>
        </form>
      </Card>

      <p className="text-center text-sm text-text">
        Don't have an account?{' '}
        <Link to="/register" className="font-medium text-accent hover:underline">
          Create one
        </Link>
      </p>
    </div>
  )
}
