import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { verifyEmail } from '../../api/auth'
import Card from '../../components/ui/Card'
import Spinner from '../../components/ui/Spinner'
import { buttonClasses } from '../../components/ui/Button'

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [status, setStatus] = useState(token ? 'pending' : 'missing') // 'pending' | 'success' | 'error' | 'missing'
  const [message, setMessage] = useState('')
  const ranRef = useRef(false)

  useEffect(() => {
    if (!token || ranRef.current) return
    ranRef.current = true
    verifyEmail(token)
      .then((response) => {
        setStatus('success')
        setMessage(response.message)
      })
      .catch((error) => {
        setStatus('error')
        setMessage(error.message)
      })
  }, [token])

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-text-h">Verify your email</h1>
      </div>

      <Card>
        {status === 'pending' && (
          <div className="flex justify-center py-4">
            <Spinner label="Verifying your email…" />
          </div>
        )}

        {status === 'missing' && (
          <p role="alert" className="rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
            No verification code found in this link. Check the link in your email, or request a new one from the
            login page.
          </p>
        )}

        {status === 'success' && (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-text-h">{message}</p>
            <Link to="/login" className={buttonClasses({ className: 'w-full' })}>
              Log in
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="flex flex-col gap-3">
            <p role="alert" className="rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger">
              {message}
            </p>
            <Link to="/login" className="text-center text-sm font-medium text-accent hover:underline">
              Back to login
            </Link>
          </div>
        )}
      </Card>
    </div>
  )
}
