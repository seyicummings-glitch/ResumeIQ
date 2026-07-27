import { LoaderCircle } from 'lucide-react'
import clsx from 'clsx'

export default function Spinner({ label = 'Loading…', size = 20, className }) {
  return (
    <div className={clsx('inline-flex items-center gap-2 text-text', className)} role="status">
      <LoaderCircle size={size} className="animate-spin text-accent" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}
