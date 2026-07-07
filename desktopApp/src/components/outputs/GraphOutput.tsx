import type { GraphOutputBlock } from '@/types/backend/outputs'

interface GraphOutputProps {
  block: GraphOutputBlock
}

const WIDTH = 640
const HEIGHT = 220
const PADDING = 36

export function GraphOutput({ block }: GraphOutputProps) {
  const series = block.series[0]
  if (!series || series.points.length === 0) {
    return (
      <article className="output-block">
        {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
        <p className="output-graph__empty">No chart data available.</p>
      </article>
    )
  }

  const values = series.points.map((point) => point.y)
  const minY = Math.min(...values, 0)
  const maxY = Math.max(...values, 1)
  const rangeY = maxY - minY || 1
  const plotWidth = WIDTH - PADDING * 2
  const plotHeight = HEIGHT - PADDING * 2
  const barWidth = plotWidth / series.points.length - 8

  const bars = series.points.map((point, index) => {
    const x = PADDING + index * (plotWidth / series.points.length) + 4
    const height = ((point.y - minY) / rangeY) * plotHeight
    const y = HEIGHT - PADDING - height
    return {
      x,
      y,
      width: Math.max(barWidth, 12),
      height,
      label: String(point.x),
      value: point.y,
    }
  })

  return (
    <article className="output-block">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <svg className="output-graph" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={block.title}>
        <line x1={PADDING} y1={HEIGHT - PADDING} x2={WIDTH - PADDING} y2={HEIGHT - PADDING} stroke="#cbd5e1" />
        <line x1={PADDING} y1={PADDING} x2={PADDING} y2={HEIGHT - PADDING} stroke="#cbd5e1" />
        {bars.map((bar) => (
          <g key={`${block.id}-${bar.label}`}>
            <rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} fill="#3b82f6" rx="3" />
            <text x={bar.x + bar.width / 2} y={HEIGHT - 14} textAnchor="middle" fontSize="11" fill="#64748b">
              {bar.label}
            </text>
          </g>
        ))}
        {block.y_label ? (
          <text x={12} y={PADDING} fontSize="11" fill="#64748b">
            {block.y_label}
          </text>
        ) : null}
      </svg>
    </article>
  )
}
