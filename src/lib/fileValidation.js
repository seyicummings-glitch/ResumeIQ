/** Mirrors the backend's own validate_file() in app/routes/resume.py so users see a clear error before a network round-trip, not after. */
export function validateFile(file, { allowedExtensions, maxSizeMb = 10 }) {
  if (!file) return 'Please choose a file.'

  const name = file.name.toLowerCase()
  const extension = name.includes('.') ? `.${name.split('.').pop()}` : ''
  if (!allowedExtensions.includes(extension)) {
    return `Unsupported file type "${extension || 'unknown'}". Allowed types: ${allowedExtensions.join(', ')}.`
  }

  if (file.size === 0) return 'That file is empty.'

  const maxBytes = maxSizeMb * 1024 * 1024
  if (file.size > maxBytes) return `File too large. Maximum allowed size is ${maxSizeMb}MB.`

  return null
}
