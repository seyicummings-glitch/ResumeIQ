import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import {
  useCreditPackages, useCreateCreditPackage, useUpdateCreditPackage, useSetCreditPackageStatus, useDeleteCreditPackage,
  usePaymentMethods, useSetPaymentMethodStatus,
} from '../../hooks/useAdminSubscriptions'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import EmptyState from '../../components/ui/EmptyState'
import { useToast } from '../../components/ui/Toast'

function formatPrice(cents, currency = 'usd') {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(cents / 100)
}

function PackageFormModal({ isOpen, onClose, editing }) {
  const createPackage = useCreateCreditPackage()
  const updatePackage = useUpdateCreditPackage()
  const { showToast } = useToast()
  const { register, handleSubmit, reset } = useForm()

  useEffect(() => {
    if (!isOpen) return
    reset({
      name: editing?.name || '',
      credits: editing?.credits || '',
      price: editing ? (editing.priceCents / 100).toFixed(2) : '',
      displayOrder: editing?.displayOrder ?? 0,
    })
  }, [isOpen, editing, reset])

  async function onSubmit(values) {
    const fields = {
      name: values.name,
      credits: parseInt(values.credits, 10),
      priceCents: Math.round(parseFloat(values.price || '0') * 100),
      displayOrder: parseInt(values.displayOrder, 10) || 0,
    }
    try {
      if (editing?.id) {
        await updatePackage.mutateAsync({ id: editing.id, fields })
        showToast('Credit package updated.', { tone: 'success' })
      } else {
        await createPackage.mutateAsync(fields)
        showToast('Credit package created.', { tone: 'success' })
      }
      onClose()
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={editing?.id ? `Edit ${editing.name}` : 'New credit package'}>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <Input label="Name" required {...register('name', { required: true })} />
        <div className="grid grid-cols-2 gap-4">
          <Input label="Credits" type="number" min="1" required {...register('credits', { required: true })} />
          <Input label="Price (USD)" type="number" step="0.01" min="0.01" required {...register('price', { required: true })} />
        </div>
        <Input label="Display order" type="number" {...register('displayOrder')} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" isLoading={createPackage.isPending || updatePackage.isPending}>
            {editing?.id ? 'Save changes' : 'Create package'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function CreditPackagesSection() {
  const { data: packages, isLoading, isError, error, refetch } = useCreditPackages()
  const setStatus = useSetCreditPackageStatus()
  const deletePackage = useDeleteCreditPackage()
  const { showToast } = useToast()

  const [editing, setEditing] = useState(null) // null closed, {} new, package object edit
  const [deleting, setDeleting] = useState(null)

  async function confirmDelete() {
    try {
      await deletePackage.mutateAsync(deleting.id)
      showToast(`${deleting.name} deleted.`, { tone: 'success' })
      setDeleting(null)
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  if (isLoading) return <div className="flex justify-center py-8"><Spinner label="Loading credit packages…" /></div>
  if (isError) return <ErrorState message={error.message} onRetry={refetch} />

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-h">Credit packages</h2>
        <Button size="sm" onClick={() => setEditing({})}>New package</Button>
      </div>

      {packages.length === 0 ? (
        <EmptyState title="No credit packages yet" description="Create a package like “100 Credits” so users can buy more usage." />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {packages.map((pkg) => (
            <Card key={pkg.id} className="flex flex-col gap-2">
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-text-h">{pkg.name}</h3>
                <Badge tone={pkg.isActive ? 'success' : 'neutral'}>{pkg.isActive ? 'Active' : 'Inactive'}</Badge>
              </div>
              <p className="text-2xl font-semibold text-text-h">{formatPrice(pkg.priceCents, pkg.currency)}</p>
              <p className="text-sm text-text">{pkg.credits.toLocaleString()} credits</p>
              <div className="mt-auto flex flex-wrap gap-2 pt-2">
                <Button variant="secondary" size="sm" onClick={() => setEditing(pkg)}>Edit</Button>
                <Button
                  variant={pkg.isActive ? 'danger' : 'secondary'}
                  size="sm"
                  onClick={() => setStatus.mutate({ id: pkg.id, isActive: !pkg.isActive })}
                >
                  {pkg.isActive ? 'Deactivate' : 'Activate'}
                </Button>
                <Button variant="danger" size="sm" onClick={() => setDeleting(pkg)}>Delete</Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <PackageFormModal isOpen={Boolean(editing)} onClose={() => setEditing(null)} editing={editing?.id ? editing : null} />
      <ConfirmDialog
        isOpen={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete credit package"
        message={`This removes "${deleting?.name || ''}" from the purchase options. It won't affect credits users already bought.`}
        confirmLabel="Delete"
        isLoading={deletePackage.isPending}
      />
    </div>
  )
}

function PaymentMethodsSection() {
  const { data: methods, isLoading, isError, error, refetch } = usePaymentMethods()
  const setStatus = useSetPaymentMethodStatus()

  if (isLoading) return <div className="flex justify-center py-8"><Spinner label="Loading payment methods…" /></div>
  if (isError) return <ErrorState message={error.message} onRetry={refetch} />

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-base font-semibold text-text-h">Payment methods</h2>
      <p className="text-sm text-text">
        Only enabled methods are offered to users at checkout. This platform never stores card numbers, CVV codes,
        or bank details — payments are processed by a payment provider (see Transactions for what's actually kept).
      </p>
      <Table>
        <TableHead>
          <Th>Method</Th>
          <Th>Status</Th>
          <Th><span className="sr-only">Toggle</span></Th>
        </TableHead>
        <TableBody>
          {methods.map((method) => (
            <tr key={method.methodKey}>
              <Td className="font-medium">{method.label}</Td>
              <Td><Badge tone={method.isEnabled ? 'success' : 'neutral'}>{method.isEnabled ? 'Enabled' : 'Disabled'}</Badge></Td>
              <Td>
                <Button
                  variant={method.isEnabled ? 'danger' : 'secondary'}
                  size="sm"
                  onClick={() => setStatus.mutate({ methodKey: method.methodKey, isEnabled: !method.isEnabled })}
                >
                  {method.isEnabled ? 'Disable' : 'Enable'}
                </Button>
              </Td>
            </tr>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export default function AdminCreditsAndPaymentsPage() {
  return (
    <div className="flex flex-col gap-8">
      <CreditPackagesSection />
      <PaymentMethodsSection />
    </div>
  )
}
