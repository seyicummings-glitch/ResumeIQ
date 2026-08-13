import { Link } from 'react-router-dom'
import { buttonClasses } from '../components/ui/Button'

export default function ForbiddenPage() {
  return (
    <div className="flex flex-col items-center gap-3 py-20 text-center">
      <h1 className="text-3xl font-semibold text-text-h">Access denied</h1>
      <p className="max-w-sm text-text">You don't have permission to view this page.</p>
      <Link to="/dashboard" className={buttonClasses()}>
        Back to dashboard
      </Link>
    </div>
  )
}
