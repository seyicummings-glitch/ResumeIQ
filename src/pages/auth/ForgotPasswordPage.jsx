import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Copy, Check } from 'lucide-react'
import { requestPasswordReset } from '../../api/auth'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
})

export default function ForgotPasswordPage() {
  const [result, setResult] = useState(null)
  const [formError, setFormError] = useState(null)
  const [copied, setCopied] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  async function onSubmit(values) {
    setFormError(null)
    try {
      const response = await requestPasswordReset(values.email)
      setResult(response)
    } catch (error) {
      setFormError(error.message)
    }
  }

  async function copyToken() {
    if (!result?.reset_token) return
    await navigator.clipboard.writeText(result.reset_token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-text-h">Forgot password</h1>
        <p className="mt-1 text-sm text-text">Enter your account email and we'll generate a reset link.</p>
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
            {result.reset_token && (
              <>
                <p className="rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning">
                  Development mode: this app doesn't send real emails yet, so your reset code is shown here directly.
                  Normally it would only be emailed to you.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 truncate rounded-lg border border-border bg-bg px-3 py-2 text-xs text-text-h">
                    {result.reset_token}
                  </code>
                  <Button type="button" variant="secondary" size="sm" onClick={copyToken} aria-label="Copy reset code">
                    {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
                  </Button>
                </div>
                <Link
                  to={`/reset-password?token=${encodeURIComponent(result.reset_token)}`}
                  className="text-center text-sm font-medium text-accent hover:underline"
                >
                  Continue to reset password
                </Link>
              </>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              required
              error={errors.email?.message}
              {...register('email')}
            />
            <Button type="submit" isLoading={isSubmitting} className="w-full">
              Send reset link
            </Button>
          </form>
        )}
      </Card>

      <p className="text-center text-sm text-text">
        Remembered your password?{' '}
        <Link to="/login" className="font-medium text-accent hover:underline">
          Log in
        </Link>
      </p>
    </div>
  )
}
