import { useState } from 'react'
import { useAdminTransactionsPage, useSubscriptionAnalytics } from '../../hooks/useAdminSubscriptions'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import EmptyState from '../../components/ui/EmptyState'
import Pagination from '../../components/ui/Pagination'

const PAGE_SIZE = 20
const STATUS_TONE = { paid: 'success', pending: 'accent', failed: 'danger', refunded: 'neutral' }

function formatCents(cents, currency = 'usd') {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format((cents || 0) / 100)
}

function AnalyticsSummary() {
  const { data, isLoading, isError } = useSubscriptionAnalytics()
  if (isLoading || isError || !data) return null

  const tiles = [
    { label: 'Total revenue', value: formatCents(data.totalRevenueCents) },
    { label: 'Active subscribers', value: data.activeSubscribers.toLocaleString() },
    { label: 'Total tokens purchased', value: data.totalCreditsPurchased.toLocaleString() },
    { label: 'Tokens consumed', value: data.creditsConsumed.toLocaleString() },
    { label: 'Users near their limit', value: data.usersNearLimit.length.toLocaleString() },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {tiles.map((tile) => (
          <Card key={tile.label} className="!p-3">
            <p className="text-xs text-text">{tile.label}</p>
            <p className="mt-1 text-lg font-semibold text-text-h">{tile.value}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-text-h">Revenue by plan</h3>
          <div className="flex flex-wrap gap-2">
            {data.revenueByPlan.length === 0 && <p className="text-sm text-text">No paid subscriptions yet.</p>}
            {data.revenueByPlan.map((row) => (
              <Badge key={row.plan} tone="accent">{row.plan} · {formatCents(row.revenueCents)}</Badge>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-text-h">Most used AI features</h3>
          <div className="flex flex-wrap gap-2">
            {data.mostUsedFeatures.length === 0 && <p className="text-sm text-text">No usage recorded yet.</p>}
            {data.mostUsedFeatures.map((row) => (
              <Badge key={row.featureKey} tone="neutral">{row.label} · {row.count}</Badge>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-text-h">Revenue by feature (estimated)</h3>
          <p className="mb-2 text-xs text-text/60">
            Credits are a shared currency, so this is a blended estimate (total credit-purchase revenue ÷ credits
            purchased, applied to credits spent per feature) — not exact per-feature attribution.
          </p>
          <div className="flex flex-wrap gap-2">
            {data.revenueByFeatureEstimated.length === 0 && <p className="text-sm text-text">No credit-funded usage yet.</p>}
            {data.revenueByFeatureEstimated.map((row) => (
              <Badge key={row.featureKey} tone="warning">{row.label} · ~{formatCents(row.estimatedRevenueCents)}</Badge>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-text-h">Users near their limit</h3>
          <div className="flex flex-wrap gap-2">
            {data.usersNearLimit.length === 0 && <p className="text-sm text-text">No one is close to their limit right now.</p>}
            {data.usersNearLimit.map((row) => (
              <Badge key={`${row.userId}-${row.featureKey}`} tone="danger">
                {row.userName} — {row.featureLabel}: {row.used}/{row.limit}
              </Badge>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-text-h">Top paying users</h3>
          <div className="flex flex-wrap gap-2">
            {data.topPayingUsers.length === 0 && <p className="text-sm text-text">No payments recorded yet.</p>}
            {data.topPayingUsers.map((row) => (
              <Badge key={row.userId} tone="accent">
                {row.userName} · {formatCents(row.totalPaidCents)}
              </Badge>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

export default function AdminTransactionsPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('all')
  const [kind, setKind] = useState('all')

  const { data, isLoading, isError, error, refetch } = useAdminTransactionsPage({
    page, pageSize: PAGE_SIZE,
    status: status === 'all' ? undefined : status,
    kind: kind === 'all' ? undefined : kind,
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-text-h">Revenue & transactions</h2>
        <p className="mt-1 text-sm text-text">
          Only what a real payment provider would ever hand back: amount, currency, status, method, and a
          transaction reference. Card numbers, CVVs, and full banking details are never stored here.
        </p>
      </div>

      <AnalyticsSummary />

      <div className="flex flex-wrap gap-3">
        <div className="w-44">
          <Select label="Status" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value) }}>
            <option value="all">All statuses</option>
            <option value="paid">Paid</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
            <option value="refunded">Refunded</option>
          </Select>
        </div>
        <div className="w-44">
          <Select label="Type" value={kind} onChange={(e) => { setPage(1); setKind(e.target.value) }}>
            <option value="all">All types</option>
            <option value="subscription">Subscription</option>
            <option value="credit_purchase">Credit purchase</option>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner label="Loading transactions…" /></div>
      ) : isError ? (
        <ErrorState message={error.message} onRetry={refetch} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No transactions yet" description="Purchases and subscription charges will show up here." />
      ) : (
        <>
          <Table>
            <TableHead>
              <Th>User</Th>
              <Th>Type</Th>
              <Th>Amount</Th>
              <Th>Method</Th>
              <Th>Status</Th>
              <Th>Date</Th>
            </TableHead>
            <TableBody>
              {data.items.map((tx) => (
                <tr key={tx.id}>
                  <Td>{tx.userName}</Td>
                  <Td className="capitalize">{tx.kind.replace('_', ' ')}{tx.creditsPurchased ? ` (${tx.creditsPurchased} credits)` : ''}</Td>
                  <Td>{formatCents(tx.amountCents, tx.currency)}</Td>
                  <Td className="capitalize">{tx.paymentMethod?.replace('_', ' ') || '—'}</Td>
                  <Td><Badge tone={STATUS_TONE[tx.status] || 'neutral'}>{tx.status}</Badge></Td>
                  <Td>{new Date(tx.createdAt).toLocaleDateString()}</Td>
                </tr>
              ))}
            </TableBody>
          </Table>
          <Pagination page={data.page} pageSize={data.pageSize} total={data.total} onPageChange={setPage} />
        </>
      )}
    </div>
  )
}
