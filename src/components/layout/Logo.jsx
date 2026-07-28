import { Zap } from 'lucide-react'
import clsx from 'clsx'

export default function Logo({ collapsed = false, className }) {
  return (
    <div className={clsx('flex items-center gap-2.5 overflow-hidden', className)}>
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md"
        style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}
      >
        <Zap size={14} color="#fff" strokeWidth={2.5} aria-hidden="true" />
      </div>
      {!collapsed && <span className="whitespace-nowrap text-sm font-bold tracking-tight text-text-h">ResumeIQ</span>}
    </div>
  )
}
