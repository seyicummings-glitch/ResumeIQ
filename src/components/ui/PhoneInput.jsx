import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Search } from 'lucide-react'
import { COUNTRY_CODES, flagEmoji } from '../../lib/countryCodes'
import { FieldWrapper, useFieldIds } from './Field'

const fieldChrome =
  'rounded-md border border-border bg-bg px-3 py-2 text-text-h placeholder:text-text/60 focus:outline-none focus-visible:outline-2 focus-visible:outline-accent transition-colors'

/** Splits a combined "+<dialCode> <rest>" value so the country button and number input can be
 * controlled independently. Values with no recognized dial code prefix (or none at all) are
 * treated as plain local numbers, so existing saved numbers aren't mangled. */
function splitPhoneValue(value) {
  const trimmed = (value || '').trim()
  if (!trimmed.startsWith('+')) return { dialCode: '', localNumber: trimmed }

  const byLongestCode = [...COUNTRY_CODES].sort((a, b) => b.dialCode.length - a.dialCode.length)
  const match = byLongestCode.find((country) => trimmed.startsWith(`${country.dialCode} `) || trimmed === country.dialCode)
  if (!match) return { dialCode: '', localNumber: trimmed }

  return { dialCode: match.dialCode, localNumber: trimmed.slice(match.dialCode.length).trim() }
}

/** Phone number field with a searchable country-code picker (search by country name or dial code). */
export default function PhoneInput({ label, value, onChange, placeholder, id }) {
  const ids = useFieldIds(id)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const containerRef = useRef(null)

  const { dialCode, localNumber } = splitPhoneValue(value)
  const selectedCountry = COUNTRY_CODES.find((country) => country.dialCode === dialCode)

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const normalizedQuery = query.trim().toLowerCase()
  const filtered = COUNTRY_CODES.filter((country) => {
    if (!normalizedQuery) return true
    return (
      country.name.toLowerCase().includes(normalizedQuery) ||
      country.dialCode.includes(normalizedQuery.replace(/^\+/, ''))
    )
  })

  function selectCountry(country) {
    setOpen(false)
    setQuery('')
    onChange(`${country.dialCode} ${localNumber}`.trim())
  }

  function handleLocalChange(event) {
    const nextLocal = event.target.value
    onChange(dialCode ? `${dialCode} ${nextLocal}`.trim() : nextLocal)
  }

  return (
    <FieldWrapper id={ids.id} label={label}>
      <div ref={containerRef} className="relative flex gap-1.5">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-haspopup="listbox"
          className={`${fieldChrome} flex w-[4.75rem] shrink-0 items-center justify-between gap-1`}
        >
          <span className="truncate text-sm">
            {selectedCountry ? `${flagEmoji(selectedCountry.iso2)} ${selectedCountry.dialCode}` : 'Code'}
          </span>
          <ChevronDown size={13} className="shrink-0 text-text/60" aria-hidden="true" />
        </button>

        <input
          id={ids.id}
          type="tel"
          autoComplete="tel-national"
          value={localNumber}
          onChange={handleLocalChange}
          placeholder={placeholder}
          className={`${fieldChrome} min-w-0 flex-1`}
        />

        {open && (
          <div className="absolute left-0 top-full z-20 mt-1 w-72 rounded-md border border-border bg-surface shadow-lg">
            <div className="flex items-center gap-2 border-b border-border p-2">
              <Search size={14} className="shrink-0 text-text/60" aria-hidden="true" />
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search country or code…"
                className="w-full bg-transparent text-sm text-text-h placeholder:text-text/50 focus:outline-none"
              />
            </div>
            <ul role="listbox" className="max-h-56 overflow-y-auto py-1">
              {filtered.length === 0 && <li className="px-3 py-2 text-sm text-text/60">No matches</li>}
              {filtered.map((country) => (
                <li key={country.iso2}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={country.dialCode === dialCode}
                    onClick={() => selectCountry(country)}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-text-h hover:bg-border/40"
                  >
                    <span aria-hidden="true">{flagEmoji(country.iso2)}</span>
                    <span className="flex-1 truncate">{country.name}</span>
                    <span className="font-mono text-xs text-text/60">{country.dialCode}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </FieldWrapper>
  )
}
