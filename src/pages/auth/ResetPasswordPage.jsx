import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { confirmPasswordReset } from '../../api/auth'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'

const schema = z
  .object({
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  })

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [formError, setFormError] = useState(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  async function onSubmit(values) {
    setFormError(null)
    try {
      await confirmPasswordReset({ token, newPassword: values.newPassword })
      showToast('Password reset — please log in with your new password.', { tone: 'success' })
      navigate('/login', { replace: true })
    } catch (error) {
      setFormError(error.message)
    }
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-text-h">Reset password</h1>
        <p className="mt-1 text-sm text-text">Choose a new password for your account.</p>
      </div>

      <Card>
        {!token && (
          <p role="alert" className="mb-4 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
            No reset code found in this link. Request a new one from the forgot password page.
          </p>
        )}
        {formError && (
          <p role="alert" className="mb-4 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            required
            hint="At least 8 characters"
            error={errors.newPassword?.message}
            {...register('newPassword')}
          />
          <Input
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            required
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />
          <Button type="submit" isLoading={isSubmitting} disabled={!token} className="w-full">
            Reset password
          </Button>
        </form>
      </Card>

      <p className="text-center text-sm text-text">
        <Link to="/forgot-password" className="font-medium text-accent hover:underline">
          Request a new reset link
        </Link>
      </p>
    </div>
  )
}
