import type {
  PlannerDebugNodeItemDto,
  PlannerDebugNodeRefDto,
  PlannerDebugViewDto,
} from '@/types/backend/inspection'
import { useRightPanelStore } from '@/store/rightPanelStore'

import './PlannerDebugView.css'

type PlannerDebugViewProps = {
  view: PlannerDebugViewDto
}

function formatNodeRef(node: PlannerDebugNodeRefDto | null): string {
  if (!node) {
    return 'none'
  }
  return `[${node.node_type}] ${node.node_id}`
}

function formatNodeRow(node: PlannerDebugNodeItemDto, includeReason: boolean): string {
  const base = `[${node.node_type}] ${node.node_id}`
  if (includeReason && node.status_reason) {
    return `${base} — ${node.status_reason}`
  }
  return base
}

type NodeGroupProps = {
  title: string
  nodes: PlannerDebugNodeItemDto[]
  showReason?: boolean
  defaultOpen?: boolean
}

function NodeGroup({ title, nodes, showReason = false, defaultOpen = false }: NodeGroupProps) {
  const openReferenceTab = useRightPanelStore((state) => state.openReferenceTab)

  return (
    <details className="planner-debug__group" open={defaultOpen}>
      <summary className="planner-debug__group-summary">
        {title} ({nodes.length})
      </summary>
      {nodes.length === 0 ? (
        <p className="planner-debug__empty">none</p>
      ) : (
        <ul className="planner-debug__list">
          {nodes.map((node) => (
            <li key={`${title}-${node.node_id}`}>
              <button
                type="button"
                className="planner-debug__row"
                onClick={() => openReferenceTab(node.node_id, node.label ?? node.node_id)}
              >
                <span className="planner-debug__row-id">{formatNodeRow(node, showReason)}</span>
                {node.label && node.label !== node.node_id ? (
                  <span className="planner-debug__row-label">{node.label}</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      )}
    </details>
  )
}

export function PlannerDebugView({ view }: PlannerDebugViewProps) {
  const { current_node, next_queued_node, goals, groups } = view

  return (
    <div className="planner-debug">
      <header className="planner-debug__header">
        <p className="planner-debug__line">
          <strong>Current node:</strong> {formatNodeRef(current_node)}
        </p>
        <p className="planner-debug__line">
          <strong>Next queued node:</strong> {formatNodeRef(next_queued_node)}
        </p>
      </header>

      <section className="planner-debug__section">
        <h3 className="planner-debug__section-title">Goal</h3>
        <ul className="planner-debug__goal-list">
          <li>
            {goals.main_goal}
            {goals.subgoals.length > 0 ? (
              <ul className="planner-debug__subgoal-list">
                {goals.subgoals.map((subgoal) => (
                  <li key={subgoal}>{subgoal}</li>
                ))}
              </ul>
            ) : null}
          </li>
        </ul>
      </section>

      <NodeGroup title="Visited in previous step" nodes={groups.visited_previous_step} />
      <NodeGroup
        title="Queue / leaf nodes awaiting expansion"
        nodes={groups.queue_leaf_nodes}
        showReason
        defaultOpen
      />
      <NodeGroup title="Visited from beginning" nodes={groups.visited_from_beginning} />
      <NodeGroup
        title="Excluded"
        nodes={groups.excluded_nodes ?? groups.excluded_blocked}
        showReason
      />
      <NodeGroup
        title="Blocked"
        nodes={groups.blocked_nodes ?? []}
        showReason
      />
    </div>
  )
}
