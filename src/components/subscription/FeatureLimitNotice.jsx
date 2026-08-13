import { Link } from 'react-router-dom'
import { TriangleAlert, X } from 'lucide-react'
import { buttonClasses } from '../ui/Button'
import Button from '../ui/Button'

/**
 * Renders the structured 402 payload feature_gate.py's FeatureAccessDenied
 * raises (see app/services/feature_gate.py) into an "Upgrade Plan / Buy
 * Credits" prompt. `detail` is `err.detail` from a caught ApiError.
 */
export default function FeatureLimitNotice({ detail, onDismiss }) {
  if (!detail) return null

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-warning bg-warning-bg p-4">
      <div className="flex items-start justify-between gap-3">
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
      <div className="flex flex-wrap gap-2 pl-6">
        {detail.canUpgrade && (
          <Link to="/subscription" className={buttonClasses({ size: 'sm' })}>
            Upgrade Plan
          </Link>
        )}
        {detail.canBuyCredits && (
          <Link to="/subscription" className={buttonClasses({ variant: 'secondary', size: 'sm' })}>
            Buy More Credits
          </Link>
        )}
      </div>
    </div>
  )
}
