import { useState } from 'react'
import { Wallet, Sparkles, ShieldCheck } from 'lucide-react'
import clsx from 'clsx'
import {
  useMySubscription, usePublicPlans, useAvailablePaymentMethods, useCreditPackagesPublic,
  useUpgradePlan, usePurchaseCredits, useMyTransactions, useMyUsageHistory,
} from '../hooks/useSubscription'
import { FEATURE_LABELS } from '../lib/subscriptionFeatures'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import Select from '../components/ui/Select'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import { useToast } from '../components/ui/Toast'

function formatCents(cents, currency = 'usd') {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format((cents || 0) / 100)
}

function UsageBar({ usage }) {
  const label = FEATURE_LABELS[usage.featureKey] || usage.featureKey
  const limit = usage.monthlyLimit
  const used = usage.monthlyUsed
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const atLimit = limit != null && used >= limit

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-text-h">{label}</span>
        <span className="text-text">
          {limit == null ? `${used} used · Unlimited` : `${used}/${limit} used`}
          {usage.isPaid && <Badge tone="accent" className="ml-2 !text-[10px]">{usage.creditCostPerUse} cr/use</Badge>}
        </span>
      </div>
      {limit != null && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-border/40">
          <div
            className={clsx('h-full rounded-full transition-[width]', atLimit ? 'bg-danger' : 'bg-accent')}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  )
}

function BuyCreditsModal({ isOpen, onClose }) {
  const { data: packages, isLoading: loadingPackages } = useCreditPackagesPublic()
  const { data: methods, isLoading: loadingMethods } = useAvailablePaymentMethods()
  const purchaseCredits = usePurchaseCredits()
  const { showToast } = useToast()
  const [packageId, setPackageId] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('')

  async function handleBuy() {
    try {
      const result = await purchaseCredits.mutateAsync({ packageId: parseInt(packageId, 10), paymentMethod })
      showToast(`Payment successful — ${result.creditsAdded} credits added. (${result.transactionId})`, { tone: 'success' })
      onClose()
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Buy credits">
      {loadingPackages || loadingMethods ? (
        <div className="flex justify-center py-8"><Spinner label="Loading options…" /></div>
      ) : (
        <div className="flex flex-col gap-4">
          <p className="flex items-start gap-2 text-xs text-text/70">
            <ShieldCheck size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
            Your payment information is securely processed by our payment provider. We do not store credit card
            details, CVV codes, or banking information.
          </p>

          <Select label="Credit package" value={packageId} onChange={(e) => setPackageId(e.target.value)}>
            <option value="">Choose a package…</option>
            {packages.map((pkg) => (
              <option key={pkg.id} value={pkg.id}>
                {pkg.name} — {formatCents(pkg.priceCents, pkg.currency)}
              </option>
            ))}
          </Select>

          <Select label="Payment method" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
            <option value="">Choose a payment method…</option>
            {methods.map((m) => (
              <option key={m.methodKey} value={m.methodKey}>{m.label}</option>
            ))}
          </Select>

          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button onClick={handleBuy} disabled={!packageId || !paymentMethod} isLoading={purchaseCredits.isPending}>
              Buy credits
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}

function UpgradePlanModal({ isOpen, onClose, currentPlanId }) {
  const { data: plans, isLoading: loadingPlans } = usePublicPlans()
  const { data: methods, isLoading: loadingMethods } = useAvailablePaymentMethods()
  const upgradePlan = useUpgradePlan()
  const { showToast } = useToast()
  const [planId, setPlanId] = useState('')
  const [billingCycle, setBillingCycle] = useState('monthly')
  const [paymentMethod, setPaymentMethod] = useState('')

  async function handleUpgrade() {
    try {
      const result = await upgradePlan.mutateAsync({ planId: parseInt(planId, 10), billingCycle, paymentMethod })
      showToast(result.message, { tone: 'success' })
      onClose()
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Upgrade plan">
      {loadingPlans || loadingMethods ? (
        <div className="flex justify-center py-8"><Spinner label="Loading plans…" /></div>
      ) : (
        <div className="flex flex-col gap-4">
          <p className="flex items-start gap-2 text-xs text-text/70">
            <ShieldCheck size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
            Your payment information is securely processed by our payment provider. ResumeIQ never saves your card
            number, CVV, or banking information.
          </p>

          <div className="flex flex-col gap-2">
            {plans.map((plan) => (
              <button
                key={plan.id}
                type="button"
                onClick={() => setPlanId(String(plan.id))}
                className={clsx(
                  'rounded-lg border p-3 text-left transition-colors',
                  String(plan.id) === planId ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50'
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-text-h">
                    {plan.name} {plan.id === currentPlanId && <Badge tone="neutral" className="ml-1 !text-[10px]">Current</Badge>}
                  </span>
                  <span className="text-sm text-text">{formatCents(plan.monthlyPriceCents, plan.currency)}/mo</span>
                </div>
                {plan.description && <p className="mt-1 text-xs text-text">{plan.description}</p>}
              </button>
            ))}
          </div>

          <Select label="Billing cycle" value={billingCycle} onChange={(e) => setBillingCycle(e.target.value)}>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
          </Select>

          <Select label="Payment method" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
            <option value="">Choose a payment method…</option>
            {methods.map((m) => (
              <option key={m.methodKey} value={m.methodKey}>{m.label}</option>
            ))}
          </Select>

          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button onClick={handleUpgrade} disabled={!planId || !paymentMethod} isLoading={upgradePlan.isPending}>
              Confirm upgrade
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}

function HistoryPanel() {
  const [tab, setTab] = useState('purchases')
  const { data: transactions, isLoading: loadingTx } = useMyTransactions({ page: 1, pageSize: 10 })
  const { data: usageHistory, isLoading: loadingUsage } = useMyUsageHistory({ page: 1, pageSize: 10 })

  return (
    <Card>
      <div className="mb-3 flex gap-2">
        <button
          type="button"
          onClick={() => setTab('purchases')}
          className={clsx('rounded-full px-3 py-1 text-sm font-medium', tab === 'purchases' ? 'bg-accent text-accent-contrast' : 'text-text/70 hover:text-text-h')}
        >
          Purchase history
        </button>
        <button
          type="button"
          onClick={() => setTab('usage')}
          className={clsx('rounded-full px-3 py-1 text-sm font-medium', tab === 'usage' ? 'bg-accent text-accent-contrast' : 'text-text/70 hover:text-text-h')}
        >
          Usage history
        </button>
      </div>

      {tab === 'purchases' && (
        loadingTx ? <Spinner label="Loading…" /> : transactions.items.length === 0 ? (
          <p className="text-sm text-text">No purchases yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {transactions.items.map((tx) => (
              <li key={tx.id} className="flex items-center justify-between border-b border-border pb-2 text-sm last:border-b-0">
                <span className="capitalize text-text-h">
                  {tx.kind.replace('_', ' ')}{tx.creditsPurchased ? ` — ${tx.creditsPurchased} credits` : ''}
                </span>
                <span className="flex items-center gap-2 text-text">
                  {formatCents(tx.amountCents, tx.currency)}
                  <Badge tone={tx.status === 'paid' ? 'success' : tx.status === 'failed' ? 'danger' : 'neutral'}>{tx.status}</Badge>
                </span>
              </li>
            ))}
          </ul>
        )
      )}

      {tab === 'usage' && (
        loadingUsage ? <Spinner label="Loading…" /> : usageHistory.items.length === 0 ? (
          <p className="text-sm text-text">No credit usage recorded yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {usageHistory.items.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between border-b border-border pb-2 text-sm last:border-b-0">
                <span className="text-text-h">
                  {entry.reason === 'usage' ? FEATURE_LABELS[entry.featureKey] || entry.featureKey : entry.reason}
                </span>
                <span className={entry.delta >= 0 ? 'text-success' : 'text-danger'}>
                  {entry.delta >= 0 ? '+' : ''}{entry.delta}
                </span>
              </li>
            ))}
          </ul>
        )
      )}
    </Card>
  )
}

export default function SubscriptionPage() {
  const { data, isLoading, isError, error, refetch } = useMySubscription()
  const [buyCreditsOpen, setBuyCreditsOpen] = useState(false)
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  if (isLoading) {
    return <div className="flex justify-center py-16"><Spinner label="Loading your plan…" /></div>
  }
  if (isError) return <ErrorState message={error.message} onRetry={refetch} />

  return (
    <div className="flex flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Plan & credits</h1>
        <p className="mt-1 text-sm text-text">Manage your subscription, credit balance, and usage.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/10">
            <Sparkles size={18} className="text-accent" aria-hidden="true" />
          </div>
          <div>
            <p className="text-xs text-text">Current plan</p>
            <p className="text-lg font-semibold text-text-h">{data.plan?.name || '—'}</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/10">
            <Wallet size={18} className="text-accent" aria-hidden="true" />
          </div>
          <div>
            <p className="text-xs text-text">Credit balance</p>
            <p className="text-lg font-semibold text-text-h">{data.creditBalance.toLocaleString()} credits</p>
          </div>
        </Card>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button onClick={() => setUpgradeOpen(true)}>
          <Sparkles size={14} aria-hidden="true" /> Upgrade Plan
        </Button>
        <Button variant="secondary" onClick={() => setBuyCreditsOpen(true)}>
          <Wallet size={14} aria-hidden="true" /> Buy Credits
        </Button>
      </div>

      <Card>
        <h2 className="mb-3 text-base font-semibold text-text-h">Usage this month</h2>
        <div className="flex flex-col gap-4">
          {data.usage.map((usage) => (
            <UsageBar key={usage.featureKey} usage={usage} />
          ))}
        </div>
      </Card>

      <HistoryPanel />

      <BuyCreditsModal isOpen={buyCreditsOpen} onClose={() => setBuyCreditsOpen(false)} />
      <UpgradePlanModal isOpen={upgradeOpen} onClose={() => setUpgradeOpen(false)} currentPlanId={data.plan?.id} />
    </div>
  )
}
