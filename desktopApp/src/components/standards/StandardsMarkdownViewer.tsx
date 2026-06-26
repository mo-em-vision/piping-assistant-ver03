import { type ReactNode } from 'react'
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

export function StandardsMarkdownViewer({ content, className }: StandardsMarkdownViewerProps) {
  const normalizedContent = normalizeBareDisplayEquations(content)

  return (
    <div className={`standards-markdown${className ? ` ${className}` : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
        urlTransform={(url) => standardsUrlTransform(url, defaultUrlTransform)}
        components={{
          h1: ({ children }) => <h1 className="standards-markdown__h1">{children}</h1>,
          h2: ({ children }) => <h2 className="standards-markdown__h2">{children}</h2>,
          h3: ({ children }) => <h3 className="standards-markdown__h3">{children}</h3>,
          p: ({ children }) => (
            <p className="standards-markdown__p">{renderRichEngineeringContent(children)}</p>
          ),
          ul: ({ children }) => <ul className="standards-markdown__ul">{children}</ul>,
          li: ({ children }) => (
            <li className="standards-markdown__li">{renderRichEngineeringContent(children)}</li>
          ),
          table: ({ children }) => (
            <div className="standards-markdown__table-wrap">
              <table className="standards-markdown__table">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="standards-markdown__th">{children}</th>,
          td: ({ children }) => (
            <td className="standards-markdown__td">{renderRichEngineeringContent(children)}</td>
          ),
          strong: MarkdownStrong,
          a: MarkdownLink,
          pre: MarkdownPre,
          code: MarkdownCode,
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  )
}
