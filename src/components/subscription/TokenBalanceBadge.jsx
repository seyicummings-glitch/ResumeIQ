import { Coins } from 'lucide-react'
import clsx from 'clsx'
import { useMySubscription } from '../../hooks/useSubscription'
import { useUpgradeModal } from './UpgradeModalProvider'

const LOW_BALANCE_THRESHOLD = 20

/** Persistent token balance shown in the app header — click to open the same upgrade/buy-credits
 * modal a blocked AI request would trigger. Polls periodically so it updates without a page
 * reload after spending tokens elsewhere (see api/client.js's balanceChangedHandler for the
 * immediate-after-use path; this is the fallback for anything that isn't a gated feature call). */
export default function TokenBalanceBadge() {
  const { data: subscription, isLoading } = useMySubscription()
  const { openUpgradeModal } = useUpgradeModal()

  if (isLoading || !subscription) return null

  const balance = subscription.creditBalance ?? 0
  const isLow = balance <= LOW_BALANCE_THRESHOLD

  return (
    <button
      type="button"
      onClick={() => openUpgradeModal({ message: `You have ${balance.toLocaleString()} tokens remaining.` })}
      title={isLow ? `Low balance — ${balance.toLocaleString()} tokens remaining` : `${balance.toLocaleString()} tokens remaining`}
      className={clsx(
        'flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs font-semibold transition-colors',
        isLow ? 'border-warning/40 bg-warning-bg text-warning' : 'border-border text-text hover:bg-border/40'
      )}
    >
      <Coins size={13} aria-hidden="true" />
      {balance.toLocaleString()}
    </button>
  )
}
