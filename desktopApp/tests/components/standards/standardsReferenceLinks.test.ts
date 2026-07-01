import { describe, expect, it } from 'vitest'

import { parseStandardsReferenceHref } from '@/components/standards/standardsReferenceLinks'

describe('parseStandardsReferenceHref', () => {
  it('parses node links without a subsection', () => {
    expect(parseStandardsReferenceHref('node:B313-304.1.2')).toEqual({
      referenceKind: 'node',
      referenceId: 'B313-304.1.2',
    })
  })

  it('parses node links with a subsection suffix', () => {
    expect(parseStandardsReferenceHref('node:B313-302.3.5/e')).toEqual({
      referenceKind: 'node',
      referenceId: 'B313-302.3.5',
      subsectionId: 'e',
    })
  })

  it('parses table links', () => {
    expect(parseStandardsReferenceHref('table:asme_b31.3_A-2')).toEqual({
      referenceKind: 'table',
      referenceId: 'asme_b31.3_A-2',
    })
  })

  it('treats legacy node:table_* links as table references', () => {
    expect(parseStandardsReferenceHref('node:table_b31_3_A-2')).toEqual({
      referenceKind: 'table',
      referenceId: 'table_b31_3_A-2',
    })
  })

  it('returns null for unsupported hrefs', () => {
    expect(parseStandardsReferenceHref('https://example.com')).toBeNull()
    expect(parseStandardsReferenceHref(undefined)).toBeNull()
  })
})
