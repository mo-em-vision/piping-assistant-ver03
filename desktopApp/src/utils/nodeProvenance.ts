import type { ActiveNodeContextDto, NodeProvenanceDto } from '@/types/backend/api'

export function activeContextToProvenance(
  context: ActiveNodeContextDto | null | undefined,
): NodeProvenanceDto | undefined {
  if (!context?.node_id || !context.hover_excerpt) {
    return undefined
  }

  return {
    node_id: context.node_id,
    standard: context.standard,
    paragraph: context.paragraph ?? null,
    hover_excerpt: context.hover_excerpt,
    source_field: context.source_field ?? null,
  }
}

export function resolveProvenance(
  primary: NodeProvenanceDto | null | undefined,
  fallback: NodeProvenanceDto | null | undefined,
): NodeProvenanceDto | undefined {
  return primary ?? fallback ?? undefined
}
