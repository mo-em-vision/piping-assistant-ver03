import { Fragment, type ReactNode } from 'react'

import ReactMarkdown, { defaultUrlTransform } from 'react-markdown'

import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'

import remarkGfm from 'remark-gfm'



import {

  extractText,

  InlineMath,

  isInlineSymbol,

  isMathExpression,

  renderRichEngineeringContent,

} from '@/components/math/engineeringMath'

import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'

import {

  parseStandardsReferenceHref,

  standardsUrlTransform,

} from '@/components/standards/standardsReferenceLinks'

import { ExternalLink } from '@/components/ui/ExternalLink'



import './ChatMarkdownContent.css'

import '@/components/math/engineeringMath.css'



interface ChatMarkdownContentProps {

  content: string

  className?: string

}



interface MarkdownCodeProps {

  className?: string

  children?: ReactNode

}



const sanitizeSchema = {

  ...defaultSchema,

  protocols: {

    ...defaultSchema.protocols,

    href: [...(defaultSchema.protocols?.href ?? []), 'node', 'table'],

  },

}



function MarkdownCode({ className, children }: MarkdownCodeProps) {

  const text = extractText(children).replace(/\n$/, '')



  if (isInlineSymbol(text) || isMathExpression(text)) {

    return <InlineMath expression={text} />

  }



  return <code className={className ?? 'chat-markdown__inline-code'}>{text}</code>

}



function MarkdownStrong({ children }: { children?: ReactNode }) {

  const text = extractText(children)

  if (isInlineSymbol(text)) {

    return <InlineMath expression={text} />

  }

  return <strong>{children}</strong>

}



function renderChatMarkdownChildren(children: ReactNode): ReactNode {
  if (children == null || children === false) {
    return null
  }
  if (typeof children === 'string') {
    return renderRichEngineeringContent(children)
  }
  if (Array.isArray(children)) {
    return children.map((child, index) => (
      <Fragment key={index}>
        {typeof child === 'string' ? renderRichEngineeringContent(child) : child}
      </Fragment>
    ))
  }
  return children
}

function MarkdownLink({ href, children }: { href?: string; children?: ReactNode }) {
  const target = parseStandardsReferenceHref(href)

  if (target) {

    const label = extractText(children).trim() || target.referenceId

    return (

      <StandardReferenceLink
        referenceKind={target.referenceKind}
        referenceId={target.referenceId}
        subsectionId={target.subsectionId}
        label={label}
        variant="inline"
      />

    )

  }



  return <ExternalLink href={href ?? '#'}>{children}</ExternalLink>

}



export function ChatMarkdownContent({ content, className }: ChatMarkdownContentProps) {

  return (

    <div className={`chat-markdown${className ? ` ${className}` : ''}`}>

      <ReactMarkdown

        remarkPlugins={[remarkGfm]}

        rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}

        urlTransform={(url) => standardsUrlTransform(url, defaultUrlTransform)}

        components={{

          h1: ({ children }) => <h1 className="chat-markdown__h1">{children}</h1>,

          h2: ({ children }) => <h2 className="chat-markdown__h2">{children}</h2>,

          h3: ({ children }) => <h3 className="chat-markdown__h3">{children}</h3>,

          p: ({ children }) => (

            <p className="chat-markdown__p">{renderChatMarkdownChildren(children)}</p>

          ),

          ul: ({ children }) => <ul className="chat-markdown__ul">{children}</ul>,

          ol: ({ children }) => <ol className="chat-markdown__ol">{children}</ol>,

          li: ({ children }) => (

            <li className="chat-markdown__li">{renderChatMarkdownChildren(children)}</li>

          ),

          td: ({ children }) => (

            <td className="chat-markdown__td">{renderRichEngineeringContent(children)}</td>

          ),

          th: ({ children }) => <th className="chat-markdown__th">{children}</th>,

          strong: MarkdownStrong,

          a: MarkdownLink,

          pre: ({ children }) => <pre className="chat-markdown__pre">{children}</pre>,

          code: MarkdownCode,

        }}

      >

        {content}

      </ReactMarkdown>

    </div>

  )

}

