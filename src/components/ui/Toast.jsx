import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { CircleCheckBig, CircleAlert, Info, X } from 'lucide-react'
import clsx from 'clsx'

const ToastContext = createContext(null)

const TONE_CONFIG = {
  success: { icon: CircleCheckBig, className: 'border-success/40 text-success' },
  error: { icon: CircleAlert, className: 'border-danger/40 text-danger' },
  info: { icon: Info, className: 'border-accent/40 text-accent' },
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const showToast = useCallback(
    (message, { tone = 'info', duration = 5000 } = {}) => {
      const id = ++idRef.current
      setToasts((current) => [...current, { id, message, tone }])
      if (duration) setTimeout(() => dismiss(id), duration)
      return id
    },
    [dismiss]
  )

  return (
    <ToastContext.Provider value={{ showToast, dismiss }}>
      {children}
      {createPortal(
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" aria-live="polite" aria-atomic="false">
          {toasts.map((toast) => {
            const config = TONE_CONFIG[toast.tone] || TONE_CONFIG.info
            const Icon = config.icon
            return (
              <div
                key={toast.id}
                role={toast.tone === 'error' ? 'alert' : 'status'}
                className={clsx(
                  'flex items-center gap-2 rounded-lg border bg-bg px-4 py-3 text-sm text-text-h shadow-lg',
                  config.className
                )}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{toast.message}</span>
                <button
                  type="button"
                  onClick={() => dismiss(toast.id)}
                  aria-label="Dismiss notification"
                  className="ml-2 text-text hover:text-text-h"
                >
                  <X size={16} aria-hidden="true" />
                </button>
              </div>
            )
          })}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}
