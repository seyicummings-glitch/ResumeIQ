import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useProfile, useUpdateProfile } from '../hooks/useProfile'
import Card from '../components/ui/Card'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorState from '../components/ui/ErrorState'
import { useToast } from '../components/ui/Toast'

export default function ProfilePage() {
  const { data: profile, isLoading, isError, error, refetch } = useProfile()
  const updateProfile = useUpdateProfile()
  const { showToast } = useToast()

  const {
    register,
    handleSubmit,
    reset,
    formState: { isDirty },
  } = useForm({ values: { fullName: profile?.full_name || '' } })

  useEffect(() => {
    if (profile) reset({ fullName: profile.full_name || '' })
  }, [profile, reset])

  async function onSubmit(values) {
    await updateProfile.mutateAsync({ full_name: values.fullName })
    showToast('Profile updated.', { tone: 'success' })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading your profile…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-h">Your profile</h1>
        <p className="mt-1 text-sm text-text">Account details from your ResumeIQ account.</p>
      </div>

      <Card className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-text">Email</p>
            <p className="font-medium text-text-h">{profile.email}</p>
          </div>
          <Badge tone={profile.role === 'admin' ? 'accent' : 'neutral'}>{profile.role}</Badge>
        </div>
        <div>
          <p className="text-sm text-text">Member since</p>
          <p className="font-medium text-text-h">{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(profile.created_at))}</p>
        </div>
      </Card>

      <Card>
        <h2 className="mb-1 text-base font-semibold text-text-h">Edit profile</h2>
        <p className="mb-4 rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning">
          Profile edits are saved on this device only, until account editing is available on the server.
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input label="Full name" autoComplete="name" {...register('fullName')} />
          <Button type="submit" isLoading={updateProfile.isPending} disabled={!isDirty} className="w-fit">
            Save changes
          </Button>
        </form>
      </Card>
    </div>
  )
}
