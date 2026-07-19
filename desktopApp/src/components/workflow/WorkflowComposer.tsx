import { useEffect, useMemo, useState } from 'react'

import { useTaskStore } from '@/store/taskStore'

import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import { DEFAULT_WORKFLOW_ASK_PROMPT } from './workflowAsk'
import type { WorkflowAsk } from './workflowAsk'
import { ComposerInlineInput } from './ComposerInlineInput'
import { MaterialSearchInput } from './MaterialSearchInput'
import { ResolutionBranchComposer } from './ResolutionBranchComposer'
import { ScrollSelectPicker } from './ScrollSelectPicker'
import { PromptHelpIcon } from './PromptHelpIcon'

import './ComposerInlineInput.css'
import './ComposerInput.css'
import './PromptHelpIcon.css'
import './WorkflowPanel.css'

interface WorkflowComposerProps {
  ask: WorkflowAsk
  disabled?: boolean
}

function initialValue(parameter: ParameterDefinitionDto): unknown {
  if (parameter.value != null) {
    return parameter.value
  }
  if (parameter.default_value != null) {
    return parameter.default_value
  }
  if (parameter.type === 'checkbox') {
    return false
  }
  if (parameter.type === 'multi_select') {
    return []
  }
  return ''
}

function initialUnit(parameter: ParameterDefinitionDto): string {
  return parameter.default_unit || parameter.units[0] || 'dimensionless'
}

function isMaterialParameter(parameter: ParameterDefinitionDto): boolean {
  return parameter.type === 'material' || parameter.name === 'material_grade'
}

function composerPlaceholder(parameter: ParameterDefinitionDto): string {
  if (isMaterialParameter(parameter)) {
    return 'Start typing to search materials…'
  }

  if (parameter.type === 'checkbox') {
    return `Confirm ${parameter.label.toLowerCase()}.`
  }

  return `Enter ${parameter.label.toLowerCase()}…`
}

function usesComposerUnitPills(parameter: ParameterDefinitionDto): boolean {
  return parameter.units.length > 0
}

function isResolutionBranchParameter(parameter: ParameterDefinitionDto | null): boolean {
  return parameter?.type === 'resolution_branch'
}

function isPipeConstructionParameter(parameter: ParameterDefinitionDto | null): boolean {
  return parameter?.name === 'pipe_construction_type' || parameter?.name === 'joint_category'
}

function usesInlineComposerRow(parameter: ParameterDefinitionDto | null): boolean {
  if (!parameter) {
    return false
  }

  return (
    parameter.type === 'text' ||
    parameter.type === 'number' ||
    parameter.type === 'unit' ||
    isMaterialParameter(parameter)
  )
}

function usesSelectionComposerRow(parameter: ParameterDefinitionDto | null): boolean {
  if (!parameter || isResolutionBranchParameter(parameter) || isPipeConstructionParameter(parameter)) {
    return false
  }

  if (parameter.type === 'checkbox') {
    return true
  }

  return (
    (parameter.type === 'dropdown' || parameter.type === 'multi_select') &&
    (parameter.options?.length ?? 0) > 0
  )
}

function renderAskPromptText(prompt: string, helpText: string | null, blocked = false) {
  return (
    <span
      className={`workflow-panel__next-step-text${
        blocked ? ' workflow-panel__next-step-text--blocked' : ''
      }`}
    >
      {prompt}
      {helpText ? <PromptHelpIcon helpText={helpText} /> : null}
    </span>
  )
}

function askHeading(ask: WorkflowAsk): string | null {
  if (!ask.prompt) {
    return null
  }

  switch (ask.kind) {
    case 'input':
      return 'Next Step:'
    case 'clarify':
      return 'Blocked:'
    case 'waiting':
      return 'Status:'
    default:
      return null
  }
}

function renderInlineComposerInput({
  parameter,
  textValue,
  unit,
  setValue,
  setUnit,
  busy,
  submitting,
  canSubmit,
  submitCurrentValue,
}: {
  parameter: ParameterDefinitionDto
  textValue: string
  unit: string
  setValue: (value: unknown) => void
  setUnit: (unit: string) => void
  busy: boolean
  submitting: boolean
  canSubmit: boolean
  submitCurrentValue: (nextValue?: unknown, displayValue?: string) => Promise<void>
}) {
  if (isMaterialParameter(parameter)) {
    return (
      <MaterialSearchInput
        inline
        value={textValue}
        onChange={setValue}
        onSubmit={(nextValue, displayValue) => void submitCurrentValue(nextValue, displayValue)}
        disabled={busy}
        submitting={submitting}
        placeholder={composerPlaceholder(parameter)}
      />
    )
  }

  const showUnits = usesComposerUnitPills(parameter)

  return (
    <ComposerInlineInput
      key={parameter.name}
      value={textValue}
      onChange={(next) => setValue(next)}
      placeholder="Value…"
      disabled={busy}
      submitting={submitting}
      canSubmit={canSubmit}
      onSubmit={() => void submitCurrentValue()}
      inputMode={parameter.type === 'text' ? 'text' : 'decimal'}
      variant={parameter.type === 'text' ? 'text' : 'numeric'}
      units={showUnits ? parameter.units : undefined}
      unit={showUnits ? unit : undefined}
      onUnitChange={showUnits ? setUnit : undefined}
      unitAriaLabel={showUnits ? `${parameter.label} unit` : undefined}
      focusKey={parameter.name}
    />
  )
}

export function WorkflowComposer({
  ask,
  disabled,
}: WorkflowComposerProps) {
  const submitParameter = useTaskStore((state) => state.submitParameter)
  const submittingParameter = useTaskStore((state) => state.submittingParameter)
  const parameter = ask.parameter

  const [value, setValue] = useState<unknown>(() => (parameter ? initialValue(parameter) : ''))
  const [unit, setUnit] = useState(() => (parameter ? initialUnit(parameter) : 'dimensionless'))
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setSubmitting(false)
    if (!parameter) {
      setValue('')
      setUnit('dimensionless')
      return
    }
    setValue(initialValue(parameter))
    setUnit(initialUnit(parameter))
  }, [parameter])

  const busy = Boolean(disabled || submitting || submittingParameter !== null)
  const processing = submittingParameter !== null || ask.kind === 'waiting'
  const lockedClassName = processing ? ' workflow-panel__next-step-inline--locked' : ''
  const options = useMemo(() => parameter?.options ?? [], [parameter])
  const askPrompt = ask.prompt
  const askHelpText = ask.help_text?.trim() || null
  const heading = askHeading(ask)

  const submitCurrentValue = async (nextValue?: unknown, displayValue?: string) => {
    if (!parameter || busy) {
      return
    }

    const resolvedValue = nextValue !== undefined ? nextValue : value
    setSubmitting(true)
    try {
      let payload: unknown = resolvedValue
      if (parameter.type === 'number' || parameter.type === 'unit') {
        payload = resolvedValue === '' ? null : Number(resolvedValue)
      }

      await submitParameter(
        parameter.name,
        payload,
        parameter.units.length > 0 ? unit : undefined,
        displayValue,
      )
      setValue(parameter.type === 'multi_select' ? [] : '')
    } finally {
      setSubmitting(false)
    }
  }

  const canSubmit =
    parameter != null &&
    !busy &&
    (parameter.type === 'checkbox' ||
      parameter.type === 'dropdown' ||
      (parameter.type === 'multi_select'
        ? Array.isArray(value) && value.length > 0
        : value !== '' && value != null))

  const textValue = value == null ? '' : String(value)
  const inlineComposerRow = usesInlineComposerRow(parameter)
  const selectionComposerRow = usesSelectionComposerRow(parameter)
  const resolutionBranchComposerRow =
    isResolutionBranchParameter(parameter) && ask.kind === 'input'
  const pipeConstructionComposerRow =
    isPipeConstructionParameter(parameter) &&
    ask.kind === 'input' &&
    (parameter?.options?.length ?? 0) > 0
  const showAskBlock = Boolean(
    askPrompt ||
      inlineComposerRow ||
      selectionComposerRow ||
      resolutionBranchComposerRow ||
      pipeConstructionComposerRow,
  )

  const renderSelectionOptions = () => {
    if (!parameter || ask.kind !== 'input') {
      return null
    }

    if (parameter.type === 'checkbox') {
      const checkboxOptions =
        options.length > 0
          ? options
          : [
              { value: 'true', label: 'Yes' },
              { value: 'false', label: 'No' },
            ]
      return (
        <div className="workflow-panel__selection-actions">
          {checkboxOptions.map((option) => {
            const optionValue = option.value === 'true' || option.value === true
            const selected = value === optionValue
            return (
              <button
                key={String(option.value)}
                type="button"
                className={`workflow-panel__option${selected ? ' workflow-panel__option--selected' : ''}`}
                disabled={busy}
                onClick={() => void submitCurrentValue(optionValue)}
              >
                <span className="workflow-panel__option-label">
                  {option.label}
                  {option.help_text ? <PromptHelpIcon helpText={option.help_text} /> : null}
                </span>
              </button>
            )
          })}
        </div>
      )
    }

    if (
      (parameter.type === 'dropdown' || parameter.type === 'multi_select') &&
      options.length > 0
    ) {
      return (
        <div
          className="workflow-panel__selection-actions"
          role="listbox"
          aria-label={`${parameter.label} options`}
        >
          {options.map((option) => {
            const selected =
              parameter.type === 'multi_select'
                ? Array.isArray(value) && value.includes(option.value)
                : value === option.value

            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={selected}
                className={`workflow-panel__option${selected ? ' workflow-panel__option--selected' : ''}`}
                disabled={busy}
                onClick={() => {
                  if (parameter.type === 'dropdown') {
                    setValue(option.value)
                    void submitCurrentValue(option.value)
                    return
                  }

                  const current = Array.isArray(value) ? value.map(String) : []
                  const next = current.includes(option.value)
                    ? current.filter((entry) => entry !== option.value)
                    : [...current, option.value]
                  setValue(next)
                }}
              >
                <span className="workflow-panel__option-label">
                  {option.label}
                  {option.help_text ? <PromptHelpIcon helpText={option.help_text} /> : null}
                </span>
              </button>
            )
          })}
        </div>
      )
    }

    return null
  }

  return (
    <div className={`workflow-panel__composer${processing ? ' workflow-panel__composer--processing' : ''}`}>
      {parameter?.editing ? (
        <p className="workflow-panel__edit-notice">
          Editing this input. Downstream values were cleared; submit to continue the workflow.
        </p>
      ) : null}
      {showAskBlock ? (
        <div className="workflow-panel__next-step">
          {heading ? (
            <p className="workflow-panel__next-step-heading">
              <strong>{heading}</strong>
            </p>
          ) : null}
          {inlineComposerRow && parameter && ask.kind === 'input' ? (
            <div className={`workflow-panel__next-step-inline${lockedClassName}`}>
              {askPrompt ? renderAskPromptText(askPrompt, askHelpText) : null}
              {renderInlineComposerInput({
                parameter,
                textValue,
                unit,
                setValue,
                setUnit,
                busy,
                submitting,
                canSubmit,
                submitCurrentValue,
              })}
            </div>
          ) : selectionComposerRow && parameter && ask.kind === 'input' ? (
            <div className={`workflow-panel__next-step-inline${lockedClassName}`}>
              {askPrompt ? renderAskPromptText(askPrompt, askHelpText) : null}
              {renderSelectionOptions()}
            </div>
          ) : pipeConstructionComposerRow && parameter && ask.kind === 'input' ? (
            <div className={`workflow-panel__next-step-inline${lockedClassName}`}>
              {askPrompt ? renderAskPromptText(askPrompt, askHelpText) : null}
              <ScrollSelectPicker
                options={parameter.options ?? []}
                value={value === '' || value == null ? null : String(value)}
                placeholder="Select pipe construction type"
                ariaLabel={`${parameter.label} options`}
                disabled={busy}
                onSelect={(nextValue) => {
                  setValue(nextValue)
                  void submitCurrentValue(nextValue)
                }}
              />
            </div>
          ) : resolutionBranchComposerRow && parameter && ask.kind === 'input' ? (
            <div className={`workflow-panel__next-step-inline${lockedClassName}`}>
              {askPrompt ? renderAskPromptText(askPrompt, askHelpText) : null}
              <ResolutionBranchComposer
                parameter={parameter}
                disabled={busy}
                onSubmit={async (name, payload, payloadUnit) => {
                  await submitParameter(name, payload, payloadUnit)
                }}
              />
            </div>
          ) : askPrompt ? (
            renderAskPromptText(askPrompt, askHelpText, ask.kind === 'clarify')
          ) : null}
        </div>
      ) : null}

      {parameter?.type === 'multi_select' && ask.kind === 'input' ? (
        <div className="workflow-panel__multi-actions">
          <button
            type="button"
            className="workflow-panel__submit workflow-panel__submit--inline"
            disabled={!canSubmit}
            onClick={() => void submitCurrentValue()}
          >
            {submitting ? 'Submitting…' : 'Submit selection'}
          </button>
        </div>
      ) : null}

      {ask.kind === 'none' && !parameter ? (
        <p className="workflow-panel__empty">{DEFAULT_WORKFLOW_ASK_PROMPT}</p>
      ) : null}
    </div>
  )
}
