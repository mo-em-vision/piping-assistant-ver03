import type { PlannerDebugViewDto } from '@/types/backend/inspection'

import { PlannerDebugView } from './PlannerDebugView'

type PlannerDevPanelProps = {
  projection: PlannerDebugViewDto
}

export function PlannerDevPanel({ projection }: PlannerDevPanelProps) {
  return <PlannerDebugView view={projection} />
}
