import { useEffect, useMemo, useState } from 'react'

import { ParameterInput } from '@/components/inputs/ParameterInput'
import { useTaskStore } from '@/store/taskStore'

import type { ParameterDefinitionDto } from '@/types/backend/parameters'

import { ComposerInput } from './ComposerInput'
import { MaterialSearchInput } from './MaterialSearchInput'

import './ComposerInput.css'
import './WorkflowPanel.css'

interface WorkflowComposerProps {
  parameter: ParameterDefinitionDto | null
  nextStepPrompt?: string | null
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

function composerPlaceholder(parameter: ParameterDefinitionDto | null): string {
  if (!parameter) {
    return 'Waiting for the next workflow step…'
  }

  if (parameter.type === 'material') {
    return 'Search ASTM materials (type at least 3 letters)…'
  }

  if (parameter.type === 'dropdown' || parameter.type === 'multi_select') {
    return 'Choose an option above…'
  }

  if (parameter.type === 'checkbox') {
    return `Confirm ${parameter.label.toLowerCase()}.`
  }

  return `Enter ${parameter.label.toLowerCase()}…`
}

export function WorkflowComposer({ parameter, nextStepPrompt, disabled }: WorkflowComposerProps) {
  const submitParameter = useTaskStore((state) => state.submitParameter)

  const [value, setValue] = useState<unknown>(() => (parameter ? initialValue(parameter) : ''))
  const [unit, setUnit] = useState(() => (parameter ? initialUnit(parameter) : 'dimensionless'))
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!parameter) {
      setValue('')
      setUnit('dimensionless')
      return
    }
    setValue(initialValue(parameter))
    setUnit(initialUnit(parameter))
  }, [parameter])

  const busy = Boolean(disabled || submitting)
  const options = useMemo(() => parameter?.options ?? [], [parameter])

  const submitCurrentValue = async (nextValue?: unknown) => {
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
        parameter.type === 'number' || parameter.type === 'unit' ? unit : undefined,
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

  return (
    <div className="workflow-panel__composer">
      {parameter?.editing ? (
        <p className="workflow-panel__edit-notice">
          Editing this input. Downstream values were cleared; submit to continue the workflow.
        </p>
      ) : null}
      {nextStepPrompt ? (
        <p className="workflow-panel__next-step">
          <strong>Next Step:</strong> {nextStepPrompt}
        </p>
      ) : null}

      {parameter && (parameter.type === 'dropdown' || parameter.type === 'multi_select') && options.length > 0 ? (
        <div className="workflow-panel__options" role="listbox" aria-label={`${parameter.label} options`}>
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
                {option.label}
              </button>
            )
          })}
        </div>
      ) : null}

      {parameter?.type === 'checkbox' ? (
        <div className="workflow-panel__checkbox-row">
          <button
            type="button"
            className={`workflow-panel__option${value === true ? ' workflow-panel__option--selected' : ''}`}
            disabled={busy}
            onClick={() => void submitCurrentValue(true)}
          >
            Yes
          </button>
          <button
            type="button"
            className={`workflow-panel__option${value === false ? ' workflow-panel__option--selected' : ''}`}
            disabled={busy}
            onClick={() => void submitCurrentValue(false)}
          >
            No
          </button>
        </div>
      ) : parameter?.type === 'material' ? (
        <MaterialSearchInput
          value={textValue}
          onChange={setValue}
          onSubmit={(nextValue) => void submitCurrentValue(nextValue)}
          disabled={busy}
          submitting={submitting}
          placeholder={composerPlaceholder(parameter)}
        />
      ) : parameter?.type === 'text' ? (
        <ComposerInput
          disabled={busy}
          submitting={submitting}
          canSubmit={canSubmit}
          placeholder={composerPlaceholder(parameter)}
          onSubmit={() => void submitCurrentValue()}
        >
          <textarea
            className="composer-input__field"
            value={textValue}
            placeholder={composerPlaceholder(parameter)}
            disabled={busy}
            rows={1}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                if (canSubmit) {
                  void submitCurrentValue()
                }
              }
            }}
          />
        </ComposerInput>
      ) : parameter?.type === 'dropdown' || parameter?.type === 'multi_select' ? (
        <ComposerInput
          disabled
          canSubmit={false}
          placeholder={composerPlaceholder(parameter)}
          onSubmit={() => undefined}
        >
          <textarea
            className="composer-input__field"
            value=""
            readOnly
            placeholder={composerPlaceholder(parameter)}
            disabled
            rows={1}
            aria-hidden="true"
          />
        </ComposerInput>
      ) : parameter ? (
        <ComposerInput
          disabled={busy}
          submitting={submitting}
          canSubmit={canSubmit}
          placeholder={composerPlaceholder(parameter)}
          onSubmit={() => void submitCurrentValue()}
        >
          <ParameterInput
            parameter={parameter}
            value={value}
            unit={unit}
            onValueChange={setValue}
            onUnitChange={setUnit}
            disabled={busy}
          />
        </ComposerInput>
      ) : (
        <ComposerInput disabled canSubmit={false} placeholder={composerPlaceholder(parameter)} onSubmit={() => undefined}>
          <textarea
            className="composer-input__field"
            value=""
            readOnly
            placeholder={composerPlaceholder(parameter)}
            disabled
            rows={1}
            aria-hidden="true"
          />
        </ComposerInput>
      )}

      {parameter?.type === 'multi_select' ? (
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
    </div>
  )
}

