import { getMe } from './auth'

const OVERRIDES_KEY = 'resumeiq_profile_overrides'

function readOverrides() {
  try {
    return JSON.parse(localStorage.getItem(OVERRIDES_KEY)) || {}
  } catch {
    return {}
  }
}

/**
 * There is no PUT /profile endpoint on the backend yet, so edits are merged
 * on top of the real /auth/me data and persisted to this device only.
 * Swapping to a real backend later means replacing the body of this
 * function with an apiRequest('/profile', { method: 'PUT', ... }) call —
 * every caller (useProfile hook, ProfilePage) stays the same.
 */
export async function getProfile() {
  const me = await getMe()
  return { ...me, ...readOverrides() }
}

export async function updateProfile(fields) {
  const overrides = { ...readOverrides(), ...fields }
  localStorage.setItem(OVERRIDES_KEY, JSON.stringify(overrides))
  return getProfile()
}
