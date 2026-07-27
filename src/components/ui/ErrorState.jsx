import { TriangleAlert } from 'lucide-react'
import Button from './Button'

export default function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-2 rounded-xl border border-danger/30 bg-danger-bg py-10 text-center">
      <TriangleAlert size={28} className="text-danger" aria-hidden="true" />
      <p className="font-medium text-danger">{title}</p>
      {message && <p className="max-w-sm text-sm text-danger/90">{message}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-2" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
