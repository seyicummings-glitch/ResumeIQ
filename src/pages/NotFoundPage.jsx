import { Link } from 'react-router-dom'
import { buttonClasses } from '../components/ui/Button'

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center gap-3 py-20 text-center">
      <h1 className="text-3xl font-semibold text-text-h">Page not found</h1>
      <p className="max-w-sm text-text">The page you're looking for doesn't exist or may have moved.</p>
      <Link to="/" className={buttonClasses()}>
        Back to home
      </Link>
    </div>
  )
}
