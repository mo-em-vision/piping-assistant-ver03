import { EngineeringMathText } from '@/components/math/engineeringMath'
import { InlineCitationText } from '@/components/standards/InlineCitationText'
import { TextOutput } from './TextOutput'

import type {
  ProseRenderBlock,
  ReferenceLinkDto,
  ResultSummaryOutputBlock,
} from '@/types/backend/outputs'

interface ResultSummaryAssumption {
  phrase?: string
  reference_label?: string
  reference_links?: ReferenceLinkDto[]
}

interface ResultSummaryAppliedParagraph {
  label?: string
  reference_links?: ReferenceLinkDto[]
}

interface ResultSummaryPayload {
  parameter_explanation?: string | null
  documentation_summary?: string | null
  applied_standard_header?: string | null
  applied_paragraphs?: ResultSummaryAppliedParagraph[]
  assumptions_intro?: string | null
  assumptions?: ResultSummaryAssumption[]
  warnings?: string[]
}

function renderReferenceLink(link: ReferenceLinkDto, key: string) {
  return <InlineCitationText key={key} link={link} linkLabel={link.label} />
}

export function ResultSummaryOutput({ block }: { block: ResultSummaryOutputBlock }) {
  const payload = (block.payload ?? {}) as ResultSummaryPayload
  const hasStructuredSections = Boolean(
    payload.documentation_summary ||
      payload.applied_paragraphs?.length ||
      payload.assumptions?.length,
  )

  if (!hasStructuredSections) {
    const prose: ProseRenderBlock = { ...block, variant: block.variant ?? 'body' }
    return <TextOutput block={prose} className="output-block--result-summary" />
  }

  const valueIntro = block.content.split('\n\n')[0]?.trim() || block.content

  return (
    <article className="output-block output-block--result-summary">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <div className="output-text">
        {valueIntro ? (
          <p className="output-text">
            <EngineeringMathText text={valueIntro} />
          </p>
        ) : null}
        {payload.parameter_explanation ? (
          <p className="output-text">
            <EngineeringMathText text={payload.parameter_explanation} />
          </p>
        ) : null}
        {payload.documentation_summary ? (
          <p className="output-text">
            <EngineeringMathText text={payload.documentation_summary} />
          </p>
        ) : null}
        {payload.applied_paragraphs?.length ? (
          <div className="output-text">
            <p className="output-text">
              <strong>{payload.applied_standard_header ?? 'Applied standard:'}</strong>
            </p>
            {payload.applied_paragraphs.map((paragraph, index) => {
              const link = paragraph.reference_links?.[0]
              return (
                <p key={`${paragraph.label ?? 'paragraph'}-${index}`} className="output-text">
                  {link ? renderReferenceLink(link, link.node_id) : paragraph.label}
                </p>
              )
            })}
          </div>
        ) : null}
        {payload.assumptions?.length ? (
          <div className="output-text">
            <p className="output-text">
              <EngineeringMathText text={payload.assumptions_intro ?? ''} />
            </p>
            <ul className="output-text output-text--list">
              {payload.assumptions.map((assumption, index) => {
                const link = assumption.reference_links?.[0]
                return (
                  <li key={`${assumption.phrase ?? 'assumption'}-${index}`}>
                    <EngineeringMathText text={`${assumption.phrase ?? ''} (according to `} />
                    {link ? (
                      <>
                        {renderReferenceLink(link, link.node_id)}
                        <EngineeringMathText text=")" />
                      </>
                    ) : (
                      <EngineeringMathText text={`${assumption.reference_label ?? ''})`} />
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        ) : null}
        {payload.warnings?.length ? (
          <div className="output-text output-text--warning">
            <p className="output-text">
              <strong>Warnings / cautions:</strong>
            </p>
            <ul className="output-text output-text--list">
              {payload.warnings.map((warning) => (
                <li key={warning}>
                  <EngineeringMathText text={warning} />
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </article>
  )
}
