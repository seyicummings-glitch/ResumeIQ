import { TriangleAlert, X } from 'lucide-react'
import Button from '../ui/Button'

/**
 * Renders the structured 402 payload feature_gate.py's FeatureAccessDenied
 * raises (see app/services/feature_gate.py) as a plain usage-limit notice.
 * `detail` is `err.detail` from a caught ApiError.
 */
export default function FeatureLimitNotice({ detail, onDismiss }) {
  if (!detail) return null

  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-warning bg-warning-bg p-4">
      <div className="flex items-start gap-2">
        <TriangleAlert size={18} className="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
        <div>
          <p className="font-medium text-text-h">{detail.message || 'You have reached your usage limit.'}</p>
          {detail.creditCost != null && (
            <p className="mt-1 text-sm text-text">
              This action costs {detail.creditCost} credit{detail.creditCost === 1 ? '' : 's'} — your balance is{' '}
              {detail.creditBalance ?? 0}.
            </p>
          )}
        </div>
      </div>
      {onDismiss && (
        <Button variant="ghost" size="sm" onClick={onDismiss} aria-label="Dismiss">
          <X size={16} aria-hidden="true" />
        </Button>
      )}
    </div>
  )
}
