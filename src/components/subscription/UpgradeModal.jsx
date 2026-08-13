import { useEffect, useState } from 'react'
import { Coins, Sparkles, Zap } from 'lucide-react'
import clsx from 'clsx'
import {
  useMySubscription,
  usePublicPlans,
  useCreditPackagesPublic,
  useAvailablePaymentMethods,
  useUpgradePlan,
  usePurchaseCredits,
} from '../../hooks/useSubscription'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Badge from '../ui/Badge'
import Select from '../ui/Select'
import Spinner from '../ui/Spinner'
import { useToast } from '../ui/Toast'

function formatPrice(cents, currency = 'usd') {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format((cents || 0) / 100)
}

/** Ticking "Xh Ym Zs" (or "Xd Yh") countdown to an ISO timestamp — null once it's passed or
 * there's nothing to count down to. */
function useCountdown(targetIso) {
  const [remainingMs, setRemainingMs] = useState(() => (targetIso ? new Date(targetIso).getTime() - Date.now() : null))

  useEffect(() => {
    if (!targetIso) {
      setRemainingMs(null)
      return
    }
    const target = new Date(targetIso).getTime()
    setRemainingMs(target - Date.now())
    const interval = setInterval(() => setRemainingMs(target - Date.now()), 1000)
    return () => clearInterval(interval)
  }, [targetIso])

  if (remainingMs == null || remainingMs <= 0) return null

  const totalSeconds = Math.floor(remainingMs / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (days > 0) return `${days}d ${hours}h ${minutes}m`
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function PlanCard({ plan, isCurrent, onUpgrade, isLoading }) {
  return (
    <div className={clsx('flex flex-col gap-2 rounded-lg border p-4', isCurrent ? 'border-accent bg-accent/5' : 'border-border')}>
      <div className="flex items-center justify-between gap-2">
        <p className="font-semibold text-text-h">{plan.name}</p>
        {isCurrent && <Badge tone="accent">Current plan</Badge>}
      </div>
      <p className="flex items-baseline gap-1">
        <span className="text-xl font-bold text-text-h">{formatPrice(plan.monthlyPriceCents, plan.currency)}</span>
        <span className="text-xs text-text/60">/ month</span>
      </p>
      <p className="flex items-center gap-1 text-sm text-text">
        <Zap size={13} className="text-accent" aria-hidden="true" />
        {plan.monthlyCredits?.toLocaleString() ?? 0} tokens / month
      </p>
      {plan.description && <p className="text-xs text-text/70">{plan.description}</p>}
      <Button size="sm" onClick={() => onUpgrade(plan)} disabled={isCurrent} isLoading={isLoading} className="mt-auto w-full">
        {isCurrent ? 'Current plan' : 'Upgrade'}
      </Button>
    </div>
  )
}

function CreditPackageCard({ pkg, onBuy, isLoading }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-4">
      <p className="flex items-center gap-1.5 font-semibold text-text-h">
        <Coins size={15} className="text-accent" aria-hidden="true" />
        {pkg.credits.toLocaleString()} tokens
      </p>
      <p className="text-xl font-bold text-text-h">{formatPrice(pkg.priceCents, pkg.currency)}</p>
      <Button size="sm" variant="secondary" onClick={() => onBuy(pkg)} isLoading={isLoading} className="mt-auto w-full">
        Buy now
      </Button>
    </div>
  )
}

export default function UpgradeModal({ detail, onClose }) {
  const isOpen = Boolean(detail)
  const { showToast } = useToast()

  const { data: subscription } = useMySubscription()
  const { data: plans } = usePublicPlans()
  const { data: packages } = useCreditPackagesPublic()
  const { data: paymentMethods } = useAvailablePaymentMethods()
  const upgradePlan = useUpgradePlan()
  const purchaseCredits = usePurchaseCredits()

  const [paymentMethod, setPaymentMethod] = useState('')
  const [buyingPlanId, setBuyingPlanId] = useState(null)
  const [buyingPackageId, setBuyingPackageId] = useState(null)

  useEffect(() => {
    if (!paymentMethod && paymentMethods?.length) setPaymentMethod(paymentMethods[0].methodKey)
  }, [paymentMethods, paymentMethod])

  const countdown = useCountdown(detail?.nextRefreshAt)

  async function handleUpgrade(plan) {
    if (!paymentMethod) return
    setBuyingPlanId(plan.id)
    try {
      const result = await upgradePlan.mutateAsync({ planId: plan.id, billingCycle: 'monthly', paymentMethod })
      showToast(result.message, { tone: 'success' })
      onClose()
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    } finally {
      setBuyingPlanId(null)
    }
  }

  async function handleBuyCredits(pkg) {
    if (!paymentMethod) return
    setBuyingPackageId(pkg.id)
    try {
      const result = await purchaseCredits.mutateAsync({ packageId: pkg.id, paymentMethod })
      showToast(`${result.creditsAdded.toLocaleString()} tokens added to your balance.`, { tone: 'success' })
      onClose()
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    } finally {
      setBuyingPackageId(null)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidthClassName="max-w-3xl"
      title={
        <span className="flex items-center gap-2">
          <Sparkles size={18} className="text-accent" aria-hidden="true" />
          AI Usage Limit Reached
        </span>
      }
    >
      <div className="flex flex-col gap-6">
        <div>
          <p className="text-sm text-text-h">
            {detail?.message || "You've used all of your available AI tokens."}
          </p>
          <p className="mt-1 text-sm text-text">Upgrade your plan or buy more tokens to keep going.</p>
        </div>

        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-bg px-4 py-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-text/60">Current tokens</p>
            <p className="text-lg font-bold text-text-h">{(subscription?.creditBalance ?? detail?.creditBalance ?? 0).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-text/60">Plan</p>
            <p className="text-lg font-bold text-text-h">{subscription?.plan?.name || '—'}</p>
          </div>
          {countdown && (
            <div>
              <p className="text-xs uppercase tracking-wide text-text/60">Free tokens refresh in</p>
              <p className="font-mono text-lg font-bold text-accent">{countdown}</p>
            </div>
          )}
        </div>

        {paymentMethods?.length > 0 && (
          <div className="max-w-xs">
            <Select label="Pay with" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
              {paymentMethods.map((m) => (
                <option key={m.methodKey} value={m.methodKey}>
                  {m.label}
                </option>
              ))}
            </Select>
          </div>
        )}

        <div>
          <p className="mb-2 text-sm font-semibold text-text-h">Upgrade Plan</p>
          {!plans ? (
            <div className="flex justify-center py-6">
              <Spinner label="Loading plans…" />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {plans.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  isCurrent={subscription?.plan?.id === plan.id}
                  onUpgrade={handleUpgrade}
                  isLoading={upgradePlan.isPending && buyingPlanId === plan.id}
                />
              ))}
            </div>
          )}
        </div>

        <div>
          <p className="mb-2 text-sm font-semibold text-text-h">Buy Credits</p>
          {!packages ? (
            <div className="flex justify-center py-6">
              <Spinner label="Loading credit packages…" />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {packages.map((pkg) => (
                <CreditPackageCard
                  key={pkg.id}
                  pkg={pkg}
                  onBuy={handleBuyCredits}
                  isLoading={purchaseCredits.isPending && buyingPackageId === pkg.id}
                />
              ))}
            </div>
          )}
        </div>

        <p className="text-xs text-text/50">
          Payments are processed by a secure payment provider — ResumeIQ never stores your card number, CVV, or expiry date.
        </p>

        <div className="flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}
