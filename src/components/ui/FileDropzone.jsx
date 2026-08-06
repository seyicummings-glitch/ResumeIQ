import { useId, useRef, useState } from 'react'
import { Upload, FileText, X } from 'lucide-react'
import clsx from 'clsx'
import { validateFile } from '../../lib/fileValidation'

/**
 * A real, always-present, keyboard-reachable <input type="file"> covers the
 * whole dropzone (so click-anywhere-to-browse and Tab+Enter both work);
 * drag-and-drop on the wrapping div is progressive enhancement on top of it,
 * never the only way to choose a file.
 * @param {{accept: string[], maxSizeMb?: number, file: File|null, onFileSelected: (file: File|null) => void, label?: string, hint?: string, error?: string, emptyTitle?: string, emptySubtitle?: string}} props
 */
export default function FileDropzone({ accept, maxSizeMb = 10, file, onFileSelected, label, hint, error, emptyTitle, emptySubtitle }) {
  const inputId = useId()
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)
  const [localError, setLocalError] = useState(null)

  const displayError = error || localError

  function handleFiles(fileList) {
    const chosen = fileList?.[0]
    if (!chosen) return
    const validationError = validateFile(chosen, { allowedExtensions: accept, maxSizeMb })
    if (validationError) {
      setLocalError(validationError)
      onFileSelected(null)
      return
    }
    setLocalError(null)
    onFileSelected(chosen)
  }

  function removeFile() {
    onFileSelected(null)
    setLocalError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-text-h">
          {label}
        </label>
      )}
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          handleFiles(event.dataTransfer.files)
        }}
        className={clsx(
          'relative flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors',
          isDragging ? 'border-accent bg-accent/5' : 'border-border',
          displayError && 'border-danger'
        )}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={accept.join(',')}
          onChange={(event) => handleFiles(event.target.files)}
          aria-describedby={displayError ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        />
        {file ? (
          <div className="pointer-events-none flex items-center gap-2 text-sm text-text-h">
            <FileText size={18} className="text-accent" aria-hidden="true" />
            <span>{file.name}</span>
            <button
              type="button"
              onClick={removeFile}
              aria-label={`Remove ${file.name}`}
              className="pointer-events-auto text-text hover:text-danger"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        ) : (
          <div className="pointer-events-none">
            <Upload size={28} className="mx-auto text-text/60" aria-hidden="true" />
            {emptyTitle ? (
              <>
                <p className="mt-2 text-sm font-semibold text-text-h">{emptyTitle}</p>
                {emptySubtitle && <p className="mt-1 text-xs text-text">{emptySubtitle}</p>}
                <p className="mt-2 text-xs">
                  or <span className="font-medium text-accent underline">click to browse</span>
                </p>
              </>
            ) : (
              <p className="mt-2 text-sm text-text">
                Drag a file here, or <span className="font-medium text-accent underline">browse</span>
              </p>
            )}
          </div>
        )}
      </div>
      {hint && !displayError && (
        <p id={`${inputId}-hint`} className="text-xs text-text">
          {hint}
        </p>
      )}
      {displayError && (
        <p id={`${inputId}-error`} className="text-xs text-danger" role="alert">
          {displayError}
        </p>
      )}
    </div>
  )
}
