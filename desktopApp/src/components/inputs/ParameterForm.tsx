import { useEffect, useMemo, useState } from 'react'

import { useTaskStore } from '@/store/taskStore'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { ParameterInput } from './ParameterInput'

import type { ParameterDefinitionDto } from '@/types/backend/parameters'

import './ParameterForm.css'

interface ParameterFormProps {
  parameters: ParameterDefinitionDto[]
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

function isEditable(parameter: ParameterDefinitionDto): boolean {
  return parameter.status === 'pending' || parameter.status === 'confirmation_required'
}

export function ParameterForm({ parameters }: ParameterFormProps) {
  const loading = useTaskStore((state) => state.loading)
  const userError = useTaskStore((state) => state.userError)
  const submitParameter = useTaskStore((state) => state.submitParameter)

  const editableParameters = useMemo(
    () => parameters.filter((parameter) => isEditable(parameter)),
    [parameters],
  )

  const [drafts, setDrafts] = useState<Record<string, { value: unknown; unit: string }>>(() =>
    Object.fromEntries(
      editableParameters.map((parameter) => [
        parameter.name,
        { value: initialValue(parameter), unit: initialUnit(parameter) },
      ]),
    ),
  )

  const [submitting, setSubmitting] = useState<string | null>(null)

  useEffect(() => {
    setDrafts(
      Object.fromEntries(
        editableParameters.map((parameter) => [
          parameter.name,
          { value: initialValue(parameter), unit: initialUnit(parameter) },
        ]),
      ),
    )
  }, [editableParameters])

  if (editableParameters.length === 0) {
    return (
      <p className="parameter-form__empty">
        All requested parameters are collected. Continue with calculation when ready.
      </p>
    )
  }

  const updateDraft = (name: string, patch: Partial<{ value: unknown; unit: string }>) => {
    setDrafts((current) => ({
      ...current,
      [name]: { ...current[name], ...patch },
    }))
  }

  const handleSubmit = async (parameter: ParameterDefinitionDto) => {
    const draft = drafts[parameter.name]
    if (!draft) {
      return
    }

    setSubmitting(parameter.name)
    try {
      let value: unknown = draft.value
      if (parameter.type === 'number' || parameter.type === 'unit') {
        value = draft.value === '' ? null : Number(draft.value)
      }

      await submitParameter(parameter.name, value, parameter.type === 'number' ? draft.unit : undefined)
    } finally {
      setSubmitting(null)
    }
  }

  return (
    <div className="parameter-form">
      {userError ? <ErrorBanner error={userError} compact /> : null}

      {editableParameters.map((parameter) => {
        const draft = drafts[parameter.name] ?? {
          value: initialValue(parameter),
          unit: initialUnit(parameter),
        }
        const busy = loading || submitting === parameter.name

        return (
          <div
            key={parameter.name}
            className={`parameter-field${parameter.status === 'confirmed' ? ' parameter-field--confirmed' : ''}`}
          >
            {parameter.type !== 'checkbox' ? (
              <label className="parameter-field__label" htmlFor={`param-${parameter.name}`}>
                {parameter.label}
                {parameter.requires_confirmation ? ' (confirm)' : ''}
              </label>
            ) : null}

            {parameter.requires_confirmation ? (
              <p className="parameter-field__hint">Confirm or change the proposed default value.</p>
            ) : null}

            <ParameterInput
              parameter={parameter}
              value={draft.value}
              unit={draft.unit}
              onValueChange={(value) => updateDraft(parameter.name, { value })}
              onUnitChange={(unit) => updateDraft(parameter.name, { unit })}
              disabled={busy}
            />

            <div className="parameter-field__actions">
              <button
                type="button"
                className="parameter-field__submit"
                onClick={() => void handleSubmit(parameter)}
                disabled={busy}
              >
                {submitting === parameter.name ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
