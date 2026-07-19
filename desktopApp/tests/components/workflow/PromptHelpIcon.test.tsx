import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { PromptHelpIcon } from '@/components/workflow/PromptHelpIcon'

describe('PromptHelpIcon', () => {
  it('renders nothing when help text is blank', () => {
    const { container } = render(<PromptHelpIcon helpText="   " />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows tooltip content on focus and hides it on blur', async () => {
    const user = userEvent.setup()
    render(<PromptHelpIcon helpText="Used in the pressure design thickness equation." />)

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

    await user.tab()
    expect(screen.getByRole('button', { name: 'Show help' })).toHaveFocus()
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'Used in the pressure design thickness equation.',
    )

    await user.tab()
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })
})
