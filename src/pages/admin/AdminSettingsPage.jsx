import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useAdminSettings, useUpdateAdminSettings } from '../../hooks/useAdminData'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Button from '../../components/ui/Button'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import { useToast } from '../../components/ui/Toast'

// The spec's four named refresh presets, stored under the hood as hours -- an admin can still
// end up with a different value than these (e.g. from an older release), so an "Other" option
// keeps the select truthful about the actual saved value rather than silently normalizing it.
const REFRESH_HOUR_PRESETS = [
  { hours: 24, label: 'Every 24 hours' },
  { hours: 48, label: 'Every 48 hours' },
  { hours: 168, label: 'Every 7 days' },
  { hours: 720, label: 'Every 30 days' },
]

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
      freeSignupCredits: Number(values.freeSignupCredits),
      freeCreditRefreshHours: Number(values.freeCreditRefreshHours),
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

          <div className="border-t border-border pt-4">
            <p className="mb-3 text-sm font-semibold text-text-h">AI token economy</p>
            <div className="flex flex-col gap-4">
              <Input
                label="Free tokens on signup"
                type="number"
                min="0"
                hint="Granted automatically to every new account."
                {...register('freeSignupCredits')}
              />
              <Select
                label="Free token refresh"
                hint="How often a Free-plan account's balance is topped back up by the amount above once it runs out."
                {...register('freeCreditRefreshHours')}
              >
                {REFRESH_HOUR_PRESETS.map((preset) => (
                  <option key={preset.hours} value={preset.hours}>
                    {preset.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <Button type="submit" isLoading={updateSettings.isPending} className="w-fit">
            Save settings
          </Button>
        </form>
      </Card>
    </div>
  )
}
