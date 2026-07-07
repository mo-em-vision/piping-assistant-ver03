import { useEffect, useMemo, useState } from 'react'



import type { ParameterDefinitionDto, ParameterOptionDto } from '@/types/backend/parameters'



import { ComposerInlineInput } from './ComposerInlineInput'

import { ScrollSelectPicker } from './ScrollSelectPicker'



import './DiameterScrollComposer.css'



type DiameterInputMode = 'nps_lookup' | 'direct_od' | 'direct_id'



interface DiameterScrollComposerProps {

  parameter: ParameterDefinitionDto

  disabled?: boolean

  onSubmit: (parameter: string, value: unknown, unit?: string) => Promise<void>

}



function defaultMode(parameter: ParameterDefinitionDto): DiameterInputMode {

  if (parameter.name === 'inside_diameter') {

    return 'direct_id'

  }

  return parameter.name === 'outside_diameter' ? 'direct_od' : 'nps_lookup'

}



function optionsForMode(

  mode: DiameterInputMode,

  parameter: ParameterDefinitionDto,

): ParameterOptionDto[] {

  const related = parameter.diameter_ui?.related_options

  if (related) {

    if (mode === 'nps_lookup') {

      return related.nominal_pipe_size ?? parameter.options ?? []

    }

    return related.outside_diameter ?? []

  }

  if (mode === 'nps_lookup') {

    return parameter.options ?? []

  }

  return []

}



export function DiameterScrollComposer({

  parameter,

  disabled,

  onSubmit,

}: DiameterScrollComposerProps) {

  const [inputMode, setInputMode] = useState<DiameterInputMode>(() => defaultMode(parameter))

  const [selectedValue, setSelectedValue] = useState<string | null>(() => {

    if (parameter.value == null || parameter.value === '') {

      return null

    }

    return String(parameter.value)

  })

  const [insideValue, setInsideValue] = useState(() => {

    if (parameter.name === 'inside_diameter' && parameter.value != null && parameter.value !== '') {

      return String(parameter.value)

    }

    return ''

  })

  const [insideUnit, setInsideUnit] = useState(

    () => parameter.default_unit || parameter.units[0] || 'mm',

  )

  const [submitting, setSubmitting] = useState(false)



  const modeOptions = useMemo(

    () => parameter.diameter_ui?.input_modes ?? [

      { value: 'nps_lookup', label: 'NPS' },

      { value: 'direct_od', label: 'Outside diameter' },

      { value: 'direct_id', label: 'Inside diameter' },

    ],

    [parameter.diameter_ui],

  )



  const scrollOptions = useMemo(

    () => optionsForMode(inputMode, parameter),

    [inputMode, parameter],

  )



  useEffect(() => {

    setSubmitting(false)

    setInputMode(defaultMode(parameter))

    setSelectedValue(

      parameter.value == null || parameter.value === '' ? null : String(parameter.value),

    )

    if (parameter.name === 'inside_diameter' && parameter.value != null && parameter.value !== '') {

      setInsideValue(String(parameter.value))

    } else if (parameter.name !== 'inside_diameter') {

      setInsideValue('')

    }

    setInsideUnit(parameter.default_unit || parameter.units[0] || 'mm')

  }, [parameter])



  useEffect(() => {

    if (inputMode === 'direct_id') {

      return

    }

    setSelectedValue(null)

  }, [inputMode])



  const busy = Boolean(disabled || submitting)



  const handleSelect = async (value: string) => {

    if (busy) {

      return

    }



    setSelectedValue(value)

    setSubmitting(true)

    try {

      if (inputMode === 'nps_lookup') {

        await onSubmit('nominal_pipe_size', value)

      } else {

        await onSubmit('outside_diameter', Number(value), 'mm')

      }

    } finally {

      setSubmitting(false)

    }

  }



  const handleInsideSubmit = async () => {

    if (busy || insideValue.trim() === '') {

      return

    }



    setSubmitting(true)

    try {

      await onSubmit('inside_diameter', Number(insideValue), insideUnit)

    } finally {

      setSubmitting(false)

    }

  }



  const listLabel =

    inputMode === 'nps_lookup'

      ? 'Nominal pipe size options from ASME B36.10'

      : 'Outside diameter options from ASME B36.10'



  const placeholder =

    inputMode === 'nps_lookup' ? 'Select pipe size' : 'Select outside diameter'



  const insideUnits = parameter.name === 'inside_diameter'

    ? parameter.units

    : ['in', 'mm']



  return (

    <div className="workflow-panel__selection-actions diameter-scroll-composer">

      <div

        className="diameter-scroll-composer__modes"

        role="tablist"

        aria-label="Diameter input mode"

      >

        {modeOptions.map((mode) => {

          const active = inputMode === mode.value

          return (

            <button

              key={mode.value}

              type="button"

              role="tab"

              aria-selected={active}

              className={`diameter-scroll-composer__mode${active ? ' diameter-scroll-composer__mode--active' : ''}`}

              disabled={busy}

              onClick={() => setInputMode(mode.value as DiameterInputMode)}

            >

              {mode.label}

            </button>

          )

        })}

      </div>



      {inputMode === 'direct_id' ? (

        <ComposerInlineInput

          value={insideValue}

          onChange={setInsideValue}

          placeholder="Enter inside diameter"

          disabled={busy}

          submitting={submitting}

          canSubmit={insideValue.trim() !== ''}

          onSubmit={() => void handleInsideSubmit()}

          inputMode="decimal"

          variant="numeric"

          units={insideUnits}

          unit={insideUnit}

          onUnitChange={setInsideUnit}

          unitAriaLabel="Inside diameter unit"

          focusKey={`${parameter.name}-inside`}

        />

      ) : (

        <ScrollSelectPicker

          options={scrollOptions}

          value={selectedValue}

          placeholder={placeholder}

          onSelect={(value) => void handleSelect(value)}

          disabled={busy}

          ariaLabel={listLabel}

        />

      )}

    </div>

  )

}


