import { useMemo } from 'react'

import { buildTaskStateViewModel } from '@/store/taskStateManager'
import { useTaskStore } from '@/store/taskStore'

export function useActiveTaskViewModel() {
  const activeTaskState = useTaskStore((state) => state.activeTaskState)

  return useMemo(() => buildTaskStateViewModel(activeTaskState), [activeTaskState])
}
