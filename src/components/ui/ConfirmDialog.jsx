import Modal from './Modal'
import Button from './Button'

/** Confirmation dialog for destructive actions with more than one consequence
 * (e.g. deleting an account also affects its resumes/analyses) — single-field
 * toggles (like activate/deactivate) should keep using an inline confirm-swap
 * instead, matching the existing convention in AdminUsersPage. */
export default function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Delete',
  tone = 'danger',
  isLoading = false,
}) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant={tone} size="sm" onClick={onConfirm} isLoading={isLoading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-text">{message}</p>
    </Modal>
  )
}
