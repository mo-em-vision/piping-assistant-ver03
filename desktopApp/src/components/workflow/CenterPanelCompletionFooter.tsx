import { RelatedWorkflowsBlock } from '@/components/workflow/RelatedWorkflowsBlock'
import { TaskCompletionNextSteps } from '@/components/workflow/TaskCompletionNextSteps'

import type { NextWorkflowsOutputBlock } from '@/types/backend/outputs'

import './CenterPanelCompletionFooter.css'

interface CenterPanelCompletionFooterProps {
  taskId: string
  relatedWorkflowsBlock: NextWorkflowsOutputBlock | null
}

export function CenterPanelCompletionFooter({
  taskId,
  relatedWorkflowsBlock,
}: CenterPanelCompletionFooterProps) {
  return (
    <div className="center-panel-completion-footer">
      {relatedWorkflowsBlock ? <RelatedWorkflowsBlock block={relatedWorkflowsBlock} /> : null}
      <TaskCompletionNextSteps taskId={taskId} />
    </div>
  )
}
