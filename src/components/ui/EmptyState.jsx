import { Inbox } from 'lucide-react'

export default function EmptyState({ icon: Icon = Inbox, title, description, action }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-12 text-center">
      <Icon size={32} className="text-text/60" aria-hidden="true" />
      <p className="font-medium text-text-h">{title}</p>
      {description && <p className="max-w-sm text-sm text-text">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
