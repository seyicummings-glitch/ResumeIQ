import { z } from 'zod'

export const PASSWORD_REQUIREMENTS_TEXT =
  '8-20 characters, including an uppercase letter, a lowercase letter, a number, and a special character.'

// Shared across registration, password reset, and change-password forms so
// the rule can never drift between them. Mirrors the backend's
// validate_password_strength (app/schemas.py) — keep both in sync.
export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .max(20, 'Password must be at most 20 characters')
  .regex(/[A-Z]/, 'Password must include at least one uppercase letter')
  .regex(/[a-z]/, 'Password must include at least one lowercase letter')
  .regex(/[0-9]/, 'Password must include at least one number')
  .regex(/[^A-Za-z0-9]/, 'Password must include at least one special character')
