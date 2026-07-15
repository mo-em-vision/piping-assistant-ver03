import { useEffect, useMemo, useState } from 'react'

import type { ParameterDefinitionDto } from '@/types/backend/parameters'

import { ComposerInlineInput } from './ComposerInlineInput'
import { ScrollSelectPicker } from './ScrollSelectPicker'

import './ResolutionBranchComposer.css'

interface ResolutionBranchComposerProps {
  parameter: ParameterDefinitionDto
  disabled?: boolean
  onSubmit: (parameter: string, value: unknown, unit?: string) => Promise<void>
}

export function ResolutionBranchComposer({
  parameter,
  disabled,
  onSubmit,
}: ResolutionBranchComposerProps) {
  const resolutionUi = parameter.resolution_ui
  const branches = resolutionUi?.branches ?? []
  const branchFactKey =
    resolutionUi?.branch_fact_key ?? `${parameter.name}__resolution_branch`

  const defaultBranchId = resolutionUi?.default_value ?? branches[0]?.id ?? null

  const [activeBranchId, setActiveBranchId] = useState<string | null>(
    () => resolutionUi?.active_branch ?? defaultBranchId,
  )
  const [numericValue, setNumericValue] = useState(() => {
    if (parameter.value == null || parameter.value === '') {
      return ''
    }
    return String(parameter.value)
  })
  const [numericUnit, setNumericUnit] = useState(
    () => parameter.default_unit || parameter.units[0] || 'mm',
  )
  const [selectedValue, setSelectedValue] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const activeBranch = useMemo(
    () => branches.find((branch) => branch.id === activeBranchId) ?? branches[0] ?? null,
    [activeBranchId, branches],
  )

  useEffect(() => {
    setSubmitting(false)
    setActiveBranchId(resolutionUi?.active_branch ?? defaultBranchId)
    setNumericValue(
      parameter.value == null || parameter.value === '' ? '' : String(parameter.value),
    )
    setNumericUnit(parameter.default_unit || parameter.units[0] || 'mm')
    setSelectedValue(null)
  }, [parameter, resolutionUi?.active_branch, resolutionUi?.default_value, branches, defaultBranchId])

  const busy = Boolean(disabled || submitting)

  const handleBranchSelect = async (branchId: string) => {
    if (busy || branchId === activeBranchId) {
      return
    }
    setActiveBranchId(branchId)
    setSubmitting(true)
    try {
      await onSubmit(branchFactKey, branchId)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDropdownSelect = async (value: string) => {
    if (busy || !activeBranch?.submit_parameter) {
      return
    }
    setSelectedValue(value)
    setSubmitting(true)
    try {
      await onSubmit(activeBranch.submit_parameter, value)
    } finally {
      setSubmitting(false)
    }
  }

  const handleNumericSubmit = async () => {
    if (busy || numericValue.trim() === '') {
      return
    }
    setSubmitting(true)
    try {
      await onSubmit(parameter.name, Number(numericValue), numericUnit)
    } finally {
      setSubmitting(false)
    }
  }

  if (!activeBranch) {
    return null
  }

  const composer = activeBranch.composer
  const isNumeric = composer?.type === 'number' || composer?.type === 'unit'

  return (
    <div className="workflow-panel__selection-actions resolution-branch-composer">
      <div
        className="resolution-branch-composer__modes"
        role="tablist"
        aria-label={`${parameter.label} input mode`}
      >
        {branches.map((branch) => {
          const active = branch.id === activeBranch.id
          return (
            <button
              key={branch.id}
              type="button"
              role="tab"
              aria-selected={active}
              className={`resolution-branch-composer__mode${
                active ? ' resolution-branch-composer__mode--active' : ''
              }`}
              disabled={busy}
              onClick={() => void handleBranchSelect(branch.id)}
            >
              {branch.label}
            </button>
          )
        })}
      </div>

      {isNumeric ? (
        <ComposerInlineInput
          value={numericValue}
          onChange={setNumericValue}
          placeholder={`Enter ${parameter.label.toLowerCase()}`}
          disabled={busy}
          submitting={submitting}
          canSubmit={numericValue.trim() !== ''}
          onSubmit={() => void handleNumericSubmit()}
          inputMode="decimal"
          variant="numeric"
          units={composer?.units?.length ? composer.units : parameter.units}
          unit={numericUnit}
          onUnitChange={setNumericUnit}
          unitAriaLabel={`${parameter.label} unit`}
          focusKey={`${parameter.name}-${activeBranch.id}`}
        />
      ) : (
        <ScrollSelectPicker
          options={composer?.options ?? parameter.options ?? []}
          value={selectedValue}
          placeholder={`Select ${activeBranch.label.toLowerCase()}`}
          onSelect={(value) => void handleDropdownSelect(value)}
          disabled={busy}
          ariaLabel={`${activeBranch.label} options`}
        />
      )}
    </div>
  )
}
