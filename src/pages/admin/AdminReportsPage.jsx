import { useAdminReports, useUpdateReportStatus } from '../../hooks/useAdminData'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Badge from '../../components/ui/Badge'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import EmptyState from '../../components/ui/EmptyState'
import { useToast } from '../../components/ui/Toast'
import { Flag } from 'lucide-react'

export default function AdminReportsPage() {
  const { data, isLoading, isError, error, refetch } = useAdminReports()
  const updateStatus = useUpdateReportStatus()
  const { showToast } = useToast()

  async function handleStatusChange(report, status) {
    await updateStatus.mutateAsync({ id: report.id, status })
    showToast(`Report marked as ${status}.`, { tone: 'success' })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading reports…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-4">
      {data.length === 0 ? (
        <EmptyState icon={Flag} title="No reports" description="Nothing has been flagged for review." />
      ) : (
        <Table>
          <TableHead>
            <Th>Reported by</Th>
            <Th>Reason</Th>
            <Th>Target</Th>
            <Th>Date</Th>
            <Th>Status</Th>
          </TableHead>
          <TableBody>
            {data.map((report) => (
              <tr key={report.id}>
                <Td>{report.reporterEmail}</Td>
                <Td className="max-w-[220px]">{report.reason}</Td>
                <Td className="max-w-[220px]">
                  <Badge tone="neutral" className="mb-1">
                    {report.targetType}
                  </Badge>
                  <div className="truncate" title={report.targetLabel}>
                    {report.targetLabel}
                  </div>
                </Td>
                <Td>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(report.createdAt))}</Td>
                <Td>
                  <Select
                    aria-label={`Status for report from ${report.reporterEmail}`}
                    value={report.status}
                    onChange={(event) => handleStatusChange(report, event.target.value)}
                  >
                    <option value="open">Open</option>
                    <option value="resolved">Resolved</option>
                    <option value="dismissed">Dismissed</option>
                  </Select>
                </Td>
              </tr>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
