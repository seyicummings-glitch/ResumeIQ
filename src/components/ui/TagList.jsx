import { useState } from 'react'
import Badge from './Badge'
import Modal from './Modal'

/**
 * Shows up to `max` items as badges, followed by a "+N more" badge when there are more —
 * clicking it opens a modal listing every item. Keeps skill/tag/keyword lists from blowing out
 * table rows and card widths across the app (Dashboard, Version History, Skill Assessment,
 * Analysis Results, etc.) while still letting the user see the complete list on demand.
 */
export default function TagList({ items, max = 6, tone = 'neutral', label = 'items', title }) {
  const [showAll, setShowAll] = useState(false)

  if (!items || items.length === 0) return null

  const visible = items.slice(0, max)
  const remaining = items.length - max

  return (
    <>
      <div className="flex flex-wrap gap-1">
        {visible.map((item) => (
          <Badge key={item} tone={tone}>
            {item}
          </Badge>
        ))}
        {remaining > 0 && (
          <button
            type="button"
            onClick={() => setShowAll(true)}
            aria-label={`Show all ${items.length} ${label}`}
            className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <Badge tone="accent" className="cursor-pointer hover:opacity-80">
              +{remaining} more
            </Badge>
          </button>
        )}
      </div>

      <Modal isOpen={showAll} onClose={() => setShowAll(false)} title={title || `All ${label} (${items.length})`}>
        <div className="flex max-h-96 flex-wrap gap-1.5 overflow-y-auto">
          {items.map((item) => (
            <Badge key={item} tone={tone}>
              {item}
            </Badge>
          ))}
        </div>
      </Modal>
    </>
  )
}
