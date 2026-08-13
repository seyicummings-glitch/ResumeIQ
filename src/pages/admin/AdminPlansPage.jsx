import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Pencil, Zap } from 'lucide-react'
import {
  useAdminPlansPage,
  useCreatePlan,
  useUpdatePlan,
  useSetPlanStatus,
  useDeletePlan,
} from '../../hooks/useAdminSubscriptions'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import TextArea from '../../components/ui/TextArea'
import Select from '../../components/ui/Select'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import EmptyState from '../../components/ui/EmptyState'
import { useToast } from '../../components/ui/Toast'

function formatPrice(cents, currency) {
  if (cents === null || cents === undefined) return '—'
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'usd' }).format(cents / 100)
}

function PlanCard({ plan, onEdit, onToggleStatus, onDelete, isTogglingStatus }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-text-h">{plan.name}</h3>
          <p className="font-mono text-xs text-text/60">{plan.slug}</p>
        </div>
        <Badge tone={plan.isActive ? 'success' : 'neutral'}>{plan.isActive ? 'Active' : 'Inactive'}</Badge>
      </div>

      <p className="text-sm text-text">{plan.description || 'No description.'}</p>

      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-semibold text-text-h">{formatPrice(plan.monthlyPriceCents, plan.currency)}</span>
        <span className="text-sm text-text">/ month</span>
      </div>
      {plan.yearlyPriceCents != null && (
        <p className="text-xs text-text">{formatPrice(plan.yearlyPriceCents, plan.currency)} / year</p>
      )}
      <p className="flex items-center gap-1 text-sm text-text-h">
        <Zap size={13} className="text-accent" aria-hidden="true" />
        {(plan.monthlyCredits || 0).toLocaleString()} tokens / month
      </p>

      <div className="mt-auto flex flex-wrap gap-2 pt-2">
        <Button variant="secondary" size="sm" onClick={() => onEdit(plan)}>
          <Pencil size={14} aria-hidden="true" />
          Edit
        </Button>
        <Button
          variant={plan.isActive ? 'danger' : 'secondary'}
          size="sm"
          onClick={() => onToggleStatus(plan)}
          isLoading={isTogglingStatus}
        >
          {plan.isActive ? 'Deactivate' : 'Activate'}
        </Button>
        <Button variant="danger" size="sm" onClick={() => onDelete(plan)}>
          Delete
        </Button>
      </div>
    </Card>
  )
}

function PlanFormModal({ isOpen, onClose, plan, register, handleSubmit, onSubmit, isLoading }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={plan ? `Edit ${plan.name}` : 'New plan'}>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <Input label="Name" required {...register('name', { required: true })} />
        <Input label="Slug" required disabled={Boolean(plan)} hint={plan ? 'Slug cannot be changed after creation.' : 'Stable identifier, e.g. "premium".'} {...register('slug', { required: true })} />
        <TextArea label="Description" {...register('description')} />
        <div className="grid grid-cols-2 gap-4">
          <Input label="Monthly price (USD)" type="number" step="0.01" min="0" required {...register('monthlyPrice', { required: true })} />
          <Input label="Yearly price (USD, optional)" type="number" step="0.01" min="0" {...register('yearlyPrice')} />
        </div>
        <Input
          label="Included tokens / month"
          type="number"
          min="0"
          hint="Granted to the subscriber's balance when they (re-)subscribe to this plan."
          {...register('monthlyCredits')}
        />
        <Input label="Display order" type="number" {...register('displayOrder')} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {plan ? 'Save changes' : 'Create plan'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default function AdminPlansPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const debouncedSearch = useDebouncedValue(search, 300)

  const { data, isLoading, isError, error, refetch } = useAdminPlansPage({
    page: 1,
    pageSize: 50,
    search: debouncedSearch,
    status: statusFilter === 'all' ? undefined : statusFilter,
  })
  const createPlan = useCreatePlan()
  const updatePlan = useUpdatePlan()
  const setPlanStatus = useSetPlanStatus()
  const deletePlan = useDeletePlan()
  const { showToast } = useToast()

  const [editingPlan, setEditingPlan] = useState(null) // null closed, {} for "new", plan object for edit
  const [deletingPlan, setDeletingPlan] = useState(null)
  const planForm = useForm()

  function openCreate() {
    setEditingPlan({})
    planForm.reset({ name: '', slug: '', description: '', monthlyPrice: '', yearlyPrice: '', monthlyCredits: 0, displayOrder: 0 })
  }

  function openEdit(plan) {
    setEditingPlan(plan)
    planForm.reset({
      name: plan.name,
      slug: plan.slug,
      description: plan.description || '',
      monthlyPrice: (plan.monthlyPriceCents / 100).toFixed(2),
      yearlyPrice: plan.yearlyPriceCents != null ? (plan.yearlyPriceCents / 100).toFixed(2) : '',
      monthlyCredits: plan.monthlyCredits || 0,
      displayOrder: plan.displayOrder,
    })
  }

  async function handleFormSubmit(values) {
    const fields = {
      name: values.name,
      slug: values.slug,
      description: values.description || null,
      monthlyPriceCents: Math.round(parseFloat(values.monthlyPrice || '0') * 100),
      yearlyPriceCents: values.yearlyPrice ? Math.round(parseFloat(values.yearlyPrice) * 100) : null,
      monthlyCredits: parseInt(values.monthlyCredits, 10) || 0,
      displayOrder: parseInt(values.displayOrder, 10) || 0,
    }
    try {
      if (editingPlan?.id) {
        await updatePlan.mutateAsync({ id: editingPlan.id, fields })
        showToast('Plan updated.', { tone: 'success' })
      } else {
        await createPlan.mutateAsync(fields)
        showToast('Plan created.', { tone: 'success' })
      }
      setEditingPlan(null)
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  async function handleToggleStatus(plan) {
    await setPlanStatus.mutateAsync({ id: plan.id, isActive: !plan.isActive })
    showToast(`${plan.name} ${plan.isActive ? 'deactivated' : 'activated'}.`, { tone: 'success' })
  }

  async function confirmDelete() {
    try {
      await deletePlan.mutateAsync(deletingPlan.id)
      showToast(`${deletingPlan.name} deleted.`, { tone: 'success' })
      setDeletingPlan(null)
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading plans…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap gap-3">
          <div className="w-64">
            <Input label="Search" placeholder="Search plans…" value={search} onChange={(event) => setSearch(event.target.value)} />
          </div>
          <div className="w-40">
            <Select label="Status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">All plans</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
          </div>
        </div>
        <Button onClick={openCreate}>New plan</Button>
      </div>

      {data.items.length === 0 ? (
        <EmptyState title="No plans yet" description="Create your first subscription plan to get started." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              onEdit={openEdit}
              onToggleStatus={handleToggleStatus}
              onDelete={setDeletingPlan}
              isTogglingStatus={setPlanStatus.isPending && setPlanStatus.variables?.id === plan.id}
            />
          ))}
        </div>
      )}

      <PlanFormModal
        isOpen={Boolean(editingPlan)}
        onClose={() => setEditingPlan(null)}
        plan={editingPlan?.id ? editingPlan : null}
        register={planForm.register}
        handleSubmit={planForm.handleSubmit}
        onSubmit={handleFormSubmit}
        isLoading={createPlan.isPending || updatePlan.isPending}
      />

      <ConfirmDialog
        isOpen={Boolean(deletingPlan)}
        onClose={() => setDeletingPlan(null)}
        onConfirm={confirmDelete}
        title="Delete plan"
        message={`This permanently deletes "${deletingPlan?.name || ''}".`}
        confirmLabel="Delete plan"
        isLoading={deletePlan.isPending}
      />
    </div>
  )
}
