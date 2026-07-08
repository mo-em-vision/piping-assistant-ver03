import roleOrderJson from '../../../contracts/center_panel_report_role_order.json'

export const REPORT_ROLE_ORDER = roleOrderJson as readonly string[]

export type ReportDisplayRole = (typeof REPORT_ROLE_ORDER)[number]

export function reportRoleIndex(displayRole: string | undefined | null): number {
  const role = String(displayRole ?? '').trim()
  if (!role) {
    return REPORT_ROLE_ORDER.length
  }
  const index = REPORT_ROLE_ORDER.indexOf(role)
  return index === -1 ? REPORT_ROLE_ORDER.length : index
}
