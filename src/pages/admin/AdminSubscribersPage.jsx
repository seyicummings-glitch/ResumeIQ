import { useState } from 'react'
import { useAdminSubscribersPage } from '../../hooks/useAdminSubscriptions'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import EmptyState from '../../components/ui/EmptyState'
import Pagination from '../../components/ui/Pagination'

const STATUS_TONE = { active: 'success', trialing: 'accent', past_due: 'warning', canceled: 'danger', incomplete: 'neutral' }

const PAGE_SIZE = 20

export default function AdminSubscribersPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, isError, error, refetch } = useAdminSubscribersPage({ page, pageSize: PAGE_SIZE })

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading subscribers…" />
      </div>
    )
  }
  if (isError) return <ErrorState message={error.message} onRetry={refetch} />

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-text-h">Subscribers</h2>
        <p className="mt-1 text-sm text-text">Every user with an active subscription record, including the Free plan.</p>
      </div>

      {data.items.length === 0 ? (
        <EmptyState title="No subscribers yet" description="Subscriptions are created automatically the first time a user tries a gated AI feature." />
      ) : (
        <>
          <Table>
            <TableHead>
              <Th>User</Th>
              <Th>Plan</Th>
              <Th>Status</Th>
              <Th>Billing cycle</Th>
              <Th>Renews</Th>
            </TableHead>
            <TableBody>
              {data.items.map((row) => (
                <tr key={row.subscriptionId}>
                  <Td>
                    <p className="font-medium text-text-h">{row.userName}</p>
                    <p className="text-xs text-text/60">{row.userEmail}</p>
                  </Td>
                  <Td>{row.planName}</Td>
                  <Td>
                    <Badge tone={STATUS_TONE[row.status] || 'neutral'}>{row.status}</Badge>
                    {row.cancelAtPeriodEnd && <span className="ml-1.5 text-xs text-text/60">(cancels at period end)</span>}
                  </Td>
                  <Td className="capitalize">{row.billingCycle}</Td>
                  <Td>{row.currentPeriodEnd ? new Date(row.currentPeriodEnd).toLocaleDateString() : '—'}</Td>
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
