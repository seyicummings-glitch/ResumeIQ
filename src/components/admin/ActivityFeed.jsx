import { useAdminActivityFeed } from '../../hooks/useAdminData'
import Card from '../ui/Card'
import Spinner from '../ui/Spinner'

function timeAgo(isoTimestamp) {
  const seconds = Math.floor((Date.now() - new Date(isoTimestamp).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

/** Live, auto-polling feed of the most recent platform activity across every
 * user — see useAdminActivityFeed's refetchInterval for the "real-time
 * updates without a page refresh" requirement. */
export default function ActivityFeed() {
  const { data, isLoading, isError } = useAdminActivityFeed(20)

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-h">Live activity</h2>
        <span className="flex items-center gap-1.5 text-xs text-text/60">
          <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
          Live
        </span>
      </div>

      {isLoading && (
        <div className="flex justify-center py-6">
          <Spinner label="Loading activity…" />
        </div>
      )}

      {isError && <p className="text-sm text-text">Couldn't load recent activity.</p>}

      {data && data.activity.length === 0 && <p className="text-sm text-text">No activity recorded yet.</p>}

      {data && data.activity.length > 0 && (
        <ul className="flex max-h-96 flex-col gap-2.5 overflow-y-auto">
          {data.activity.map((entry) => (
            <li key={entry.id} className="flex items-start justify-between gap-3 border-b border-border pb-2.5 last:border-b-0 last:pb-0">
              <p className="text-sm text-text-h">{entry.text}</p>
              <span className="shrink-0 whitespace-nowrap text-xs text-text/60">{timeAgo(entry.timestamp)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
