import { createContext, useContext, type ReactNode } from 'react'

import type { ParameterDefinitionDto } from '@/types/backend/parameters'

type CenterPanelEquationFocusContextValue = {
  activeParameter: ParameterDefinitionDto | null
}

const CenterPanelEquationFocusContext = createContext<CenterPanelEquationFocusContextValue>({
  activeParameter: null,
})

export function CenterPanelEquationFocusProvider({
  activeParameter,
  children,
}: {
  activeParameter: ParameterDefinitionDto | null
  children: ReactNode
}) {
  return (
    <CenterPanelEquationFocusContext.Provider value={{ activeParameter }}>
      {children}
    </CenterPanelEquationFocusContext.Provider>
  )
}

export function useCenterPanelEquationFocus(): CenterPanelEquationFocusContextValue {
  return useContext(CenterPanelEquationFocusContext)
}
