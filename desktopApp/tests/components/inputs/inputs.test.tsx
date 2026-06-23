import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { CheckboxInput } from '@/components/inputs/CheckboxInput'
import { TextInput } from '@/components/inputs/TextInput'

describe('TextInput', () => {
  it('calls onChange with updated value', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(<TextInput value="" onChange={onChange} placeholder="Enter NPS" />)

    await user.type(screen.getByPlaceholderText('Enter NPS'), '6')

    expect(onChange).toHaveBeenCalled()
    expect(onChange.mock.calls.at(-1)?.[0]).toBe('6')
  })

  it('respects disabled state', () => {
    render(<TextInput value="locked" onChange={vi.fn()} disabled />)

    expect(screen.getByDisplayValue('locked')).toBeDisabled()
  })
})

describe('CheckboxInput', () => {
  it('toggles checked state', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(<CheckboxInput checked={false} label="Include corrosion allowance" onChange={onChange} />)

    await user.click(screen.getByRole('checkbox'))

    expect(onChange).toHaveBeenCalledWith(true)
  })
})
