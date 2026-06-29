import Editor from '@monaco-editor/react'
import { useEffect, useState } from 'react'
import 'katex/dist/katex.min.css'

import { devStudioApi } from '@/dev-studio/api/devStudioApi'
import { DisplayMath } from '@/components/math/engineeringMath'
import { CollapsibleSection, Field } from '@/dev-studio/components/fields/FieldComponents'

interface EquationEditorProps {
  pack: string
  nodeId: string
  sympy: string
  displayLatex: string
  onSympyChange: (value: string) => void
  onDisplayChange: (value: string) => void
}

export function EquationEditor({
  pack,
  nodeId,
  sympy,
  displayLatex,
  onSympyChange,
  onDisplayChange,
}: EquationEditorProps) {
  const [testValues, setTestValues] = useState('{\n  "a": 1\n}')
  const [preview, setPreview] = useState<{ valid: boolean; display?: string; error?: string } | null>(null)

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const symbolValues = JSON.parse(testValues) as Record<string, number>
        const res = await devStudioApi.previewEquation(pack, nodeId, {
          sympy,
          display_latex: displayLatex,
          symbol_values: symbolValues,
        })
        setPreview(res)
      } catch {
        setPreview({ valid: false, error: 'Invalid test values JSON' })
      }
    }, 600)
    return () => window.clearTimeout(timer)
  }, [pack, nodeId, sympy, displayLatex, testValues])

  return (
    <CollapsibleSection title="Equation Editor">
      <Field label="SymPy expression">
        <div style={{ border: '1px solid var(--ds-border)', borderRadius: 6, overflow: 'hidden' }}>
          <Editor
            height="120px"
            language="python"
            theme="vs-dark"
            value={sympy}
            onChange={(v) => onSympyChange(v ?? '')}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: 'off',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              bracketPairColorization: { enabled: true },
            }}
          />
        </div>
      </Field>
      <Field label="Display LaTeX">
        <textarea
          className="dev-studio__textarea"
          value={displayLatex}
          onChange={(e) => onDisplayChange(e.target.value)}
          rows={2}
        />
        {displayLatex && (
          <div style={{ marginTop: 8 }}>
            <DisplayMath expression={displayLatex} />
          </div>
        )}
      </Field>
      <Field label="Test values (JSON)">
        <textarea
          className="dev-studio__textarea"
          value={testValues}
          onChange={(e) => setTestValues(e.target.value)}
          rows={4}
        />
      </Field>
      {preview && (
        <div className={`dev-studio__validation${preview.valid ? '' : ' dev-studio__validation--error'}`}>
          {preview.valid ? preview.display ?? 'Valid' : preview.error}
        </div>
      )}
    </CollapsibleSection>
  )
}
