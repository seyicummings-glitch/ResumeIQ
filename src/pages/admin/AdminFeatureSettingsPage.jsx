import { useState, useEffect } from 'react'
import { useFeatureSettings, useUpdateFeatureSetting } from '../../hooks/useAdminSubscriptions'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import { useToast } from '../../components/ui/Toast'

function FeatureRow({ feature }) {
  const updateSetting = useUpdateFeatureSetting()
  const { showToast } = useToast()
  const [isPaid, setIsPaid] = useState(feature.isPaid)
  const [creditCost, setCreditCost] = useState(String(feature.creditCostPerUse))
  const [isEnabled, setIsEnabled] = useState(feature.isEnabled)

  useEffect(() => {
    setIsPaid(feature.isPaid)
    setCreditCost(String(feature.creditCostPerUse))
    setIsEnabled(feature.isEnabled)
  }, [feature])

  const dirty = isPaid !== feature.isPaid || creditCost !== String(feature.creditCostPerUse) || isEnabled !== feature.isEnabled

  async function save() {
    try {
      await updateSetting.mutateAsync({
        featureKey: feature.featureKey,
        fields: { isPaid, creditCostPerUse: parseInt(creditCost, 10) || 0, isEnabled },
      })
      showToast(`${feature.featureLabel} updated.`, { tone: 'success' })
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  return (
    <tr>
      <Td className="font-medium">{feature.featureLabel}</Td>
      <Td>
        <button
          type="button"
          onClick={() => setIsPaid((v) => !v)}
          className="inline-flex"
          aria-pressed={isPaid}
        >
          <Badge tone={isPaid ? 'warning' : 'success'}>{isPaid ? 'Paid' : 'Free'}</Badge>
        </button>
      </Td>
      <Td>
        <div className="w-24">
          <Input
            type="number"
            min="0"
            value={creditCost}
            onChange={(e) => setCreditCost(e.target.value)}
            disabled={!isPaid}
            title="Tokens deducted from the user's balance each time this feature is used"
          />
        </div>
      </Td>
      <Td>
        <button type="button" onClick={() => setIsEnabled((v) => !v)} className="inline-flex" aria-pressed={isEnabled}>
          <Badge tone={isEnabled ? 'accent' : 'neutral'}>{isEnabled ? 'Gating on' : 'Gating off'}</Badge>
        </button>
      </Td>
      <Td>
        <Button size="sm" onClick={save} disabled={!dirty} isLoading={updateSetting.isPending}>
          Save
        </Button>
      </Td>
    </tr>
  )
}

export default function AdminFeatureSettingsPage() {
  const { data, isLoading, isError, error, refetch } = useFeatureSettings()

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading feature settings…" />
      </div>
    )
  }
  if (isError) return <ErrorState message={error.message} onRetry={refetch} />

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-text-h">AI feature settings</h2>
        <p className="mt-1 text-sm text-text">
          Decide which AI features spend tokens and how many tokens each use costs. A "Free" feature never touches a
          user's balance. Changes apply immediately across the platform — no code changes or redeploys needed.
          "Gating off" bypasses the token check entirely for that feature (an emergency kill-switch), regardless of
          balance.
        </p>
      </div>

      <Table>
        <TableHead>
          <Th>Feature</Th>
          <Th>Free / Paid</Th>
          <Th>Token cost per use</Th>
          <Th>Gating</Th>
          <Th>
            <span className="sr-only">Save</span>
          </Th>
        </TableHead>
        <TableBody>
          {data.map((feature) => (
            <FeatureRow key={feature.featureKey} feature={feature} />
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
