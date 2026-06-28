import { type ReactNode, useMemo } from 'react'
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

import {
  DisplayMath,
  extractText,
  InlineMath,
  isDisplayEquationLike,
  isInlineSymbol,
  isMathExpression,
  normalizeBareDisplayEquations,
  normalizeDisplayEquation,
  renderRichEngineeringContent,
} from '@/components/math/engineeringMath'
import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import { ReferenceEditionLine } from '@/components/standards/ReferenceEditionLine'
import {
  parseStandardsReferenceHref,
  standardsUrlTransform,
} from '@/components/standards/standardsReferenceLinks'
import { ExternalLink } from '@/components/ui/ExternalLink'

import './StandardsMarkdownViewer.css'
import '@/components/math/engineeringMath.css'

interface StandardsMarkdownViewerProps {
  content: string
  className?: string
  standard?: string
  revisionYear?: number | null
}

const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), 'br'],
  protocols: {
    ...defaultSchema.protocols,
    href: [...(defaultSchema.protocols?.href ?? []), 'node', 'table'],
  },
}

interface MarkdownCodeProps {
  className?: string
  children?: ReactNode
}

function MarkdownCode({ className, children }: MarkdownCodeProps) {
  const text = extractText(children).replace(/\n$/, '')

  if (isInlineSymbol(text)) {
    return <InlineMath expression={text} />
  }

  if (isMathExpression(text)) {
    return <InlineMath expression={text} />
  }

  return <code className={className ?? 'standards-markdown__inline-code'}>{text}</code>
}

function MarkdownPre({ children }: { children?: ReactNode }) {
  const text = extractText(children).replace(/\n$/, '').trim()
  const displayEquation = normalizeDisplayEquation(text)

  if (displayEquation && isDisplayEquationLike(text)) {
    return <DisplayMath expression={displayEquation} className="standards-markdown__equation" />
  }

  return <pre className="standards-markdown__pre">{children}</pre>
}

function MarkdownStrong({ children }: { children?: ReactNode }) {
  const text = extractText(children)
  if (isInlineSymbol(text)) {
    return <InlineMath expression={text} />
  }
  return <strong>{children}</strong>
}

function MarkdownLink({
  href,
  children,
}: {
  href?: string
  children?: ReactNode
}) {
  const target = parseStandardsReferenceHref(href)
  if (target) {
    const label = extractText(children).trim() || target.referenceId
    return (
      <StandardReferenceLink
        referenceKind={target.referenceKind}
        referenceId={target.referenceId}
        subsectionId={target.subsectionId}
        label={label}
      />
    )
  }

  return <ExternalLink href={href ?? '#'}>{children}</ExternalLink>
}

const markdownComponents = {
  h1: ({ children }: { children?: ReactNode }) => <h1 className="standards-markdown__h1">{children}</h1>,
  h2: ({ children }: { children?: ReactNode }) => <h2 className="standards-markdown__h2">{children}</h2>,
  h3: ({ children }: { children?: ReactNode }) => <h3 className="standards-markdown__h3">{children}</h3>,
  p: ({ children }: { children?: ReactNode }) => (
    <p className="standards-markdown__p">{renderRichEngineeringContent(children)}</p>
  ),
  ul: ({ children }: { children?: ReactNode }) => <ul className="standards-markdown__ul">{children}</ul>,
  li: ({ children }: { children?: ReactNode }) => (
    <li className="standards-markdown__li">{renderRichEngineeringContent(children)}</li>
  ),
  table: ({ children }: { children?: ReactNode }) => (
    <div className="standards-markdown__table-wrap">
      <table className="standards-markdown__table">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: ReactNode }) => <th className="standards-markdown__th">{children}</th>,
  td: ({ children }: { children?: ReactNode }) => (
    <td className="standards-markdown__td">{renderRichEngineeringContent(children)}</td>
  ),
  strong: MarkdownStrong,
  a: MarkdownLink,
  pre: MarkdownPre,
  code: MarkdownCode,
}

function splitAfterFirstH1(content: string): { head: string; tail: string } | null {
  const index = content.search(/^#\s+/m)
  if (index === -1) {
    return null
  }

  const afterHeading = content.indexOf('\n', index)
  const splitAt = afterHeading === -1 ? content.length : afterHeading + 1
  return {
    head: content.slice(0, splitAt),
    tail: content.slice(splitAt),
  }
}

function MarkdownBlock({ content }: { content: string }) {
  if (!content.trim()) {
    return null
  }

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
      urlTransform={(url) => standardsUrlTransform(url, defaultUrlTransform)}
      components={markdownComponents}
    >
      {content}
    </ReactMarkdown>
  )
}

export function StandardsMarkdownViewer({
  content,
  className,
  standard,
  revisionYear,
}: StandardsMarkdownViewerProps) {
  const normalizedContent = normalizeBareDisplayEquations(content)
  const split = useMemo(() => {
    if (revisionYear == null || !standard) {
      return null
    }
    return splitAfterFirstH1(normalizedContent)
  }, [normalizedContent, revisionYear, standard])

  return (
    <div className={`standards-markdown${className ? ` ${className}` : ''}`}>
      {split ? (
        <>
          <MarkdownBlock content={split.head} />
          <ReferenceEditionLine standard={standard!} revisionYear={revisionYear} />
          <MarkdownBlock content={split.tail} />
        </>
      ) : (
        <MarkdownBlock content={normalizedContent} />
      )}
    </div>
  )
}
