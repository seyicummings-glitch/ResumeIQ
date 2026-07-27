/** Small artificial delay so sample-data pages show the same loading states real API calls will have. */
export function simulateLatency(ms = 350) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
