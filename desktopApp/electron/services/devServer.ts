/**
 * Normalize dev server URL for Electron on Windows where `localhost` may not match
 * the address Vite bound to (IPv6 [::1] vs IPv4 127.0.0.1).
 */
export function normalizeDevServerUrl(url: string): string {
  return url.replace('://localhost', '://127.0.0.1')
}
