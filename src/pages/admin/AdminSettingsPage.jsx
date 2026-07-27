import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useAdminSettings, useUpdateAdminSettings } from '../../hooks/useAdminData'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import { useToast } from '../../components/ui/Toast'

export default function AdminSettingsPage() {
  const { data, isLoading, isError, error, refetch } = useAdminSettings()
  const updateSettings = useUpdateAdminSettings()
  const { showToast } = useToast()

  const { register, handleSubmit, reset } = useForm()

  useEffect(() => {
    if (data) reset(data)
  }, [data, reset])

  async function onSubmit(values) {
    await updateSettings.mutateAsync({
      ...values,
      maxUploadSizeMb: Number(values.maxUploadSizeMb),
      rateLimitPerMinute: Number(values.rateLimitPerMinute),
    })
    showToast('Settings saved.', { tone: 'success' })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading settings…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning">
        Demo data: the backend has no settings endpoint yet, so these are saved on this device only. Maintenance
        mode here does not actually affect the live backend (that's controlled by its own MAINTENANCE_MODE
        environment variable).
      </p>

      <Card className="max-w-lg">
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <label className="flex items-center gap-2 text-sm font-medium text-text-h">
            <input type="checkbox" {...register('maintenanceMode')} className="h-4 w-4 rounded border-border" />
            Maintenance mode
          </label>
          <label className="flex items-center gap-2 text-sm font-medium text-text-h">
            <input type="checkbox" {...register('aiSuggestionsEnabled')} className="h-4 w-4 rounded border-border" />
            AI suggestions enabled
          </label>
          <Input label="Max upload size (MB)" type="number" min="1" {...register('maxUploadSizeMb')} />
          <Input label="Rate limit (requests / minute)" type="number" min="1" {...register('rateLimitPerMinute')} />
          <Input label="Support email" type="email" {...register('supportEmail')} />
          <Button type="submit" isLoading={updateSettings.isPending} className="w-fit">
            Save settings
          </Button>
        </form>
      </Card>
    </div>
  )
}
