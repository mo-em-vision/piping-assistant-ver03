/** MOCK_DATA — sample chat transcript for mock mode. */
import type { ChatMessageDto } from '@/types/backend/chat'

export const mockChatMessages: ChatMessageDto[] = [
  {
    id: 'mock-welcome',
    role: 'assistant',
    content:
      'Engineering assistant ready. Ask about standards, start a pipe thickness calculation, or get help with an active task.',
    timestamp: new Date().toISOString(),
    status: 'ready',
  },
]

export function mockAssistantReply(message: string, hasActiveTask: boolean): string {
  const text = message.toLowerCase()
  if (text.includes('thickness') || text.includes('pipe')) {
    return hasActiveTask
      ? 'I can explain the current thickness workflow, missing inputs, and calculation outputs. What would you like to know?'
      : 'I can help you start a pipe wall thickness calculation. Select the workflow from the left panel or ask me to walk through the required inputs.'
  }
  if (text.includes('pressure')) {
    return 'Design pressure is a required input for wall thickness design. Specify the value with units, for example 8 bar or 500 psi.'
  }
  return 'I can help with engineering workflows, standards references, and interpreting task outputs. Try asking about pipe thickness or material selection.'
}

export function mockSelectionExplanation(selectedText: string, prompt: string): string {
  const topic = selectedText.trim() || 'the selected text'
  const hasTaskContext = prompt.toLowerCase().includes('current task state')
  const intro = hasTaskContext
    ? `Here is a plain-language explanation of "${topic}" in the context of your current task.`
    : `Here is a plain-language explanation of "${topic}".`

  if (/quality factor/i.test(topic) || /\bE\b/.test(topic)) {
    return `${intro}

**Definition:** The quality factor (E) accounts for material and manufacturing quality in the wall-thickness equation. In ASME B31.3 it is taken from Tables A-1A and A-1B.

**Example:** For seamless pipe in many common services, E is often 1.0. A lower E increases the required wall thickness because it reduces the allowable strength used in the calculation.

**In your task:** E is a parameter in the pressure design thickness formula — it does not replace entering pressure, diameter, or stress values.`
  }

  return `${intro}

**Definition:** This term relates to the engineering concept you highlighted in the workspace.

**Example:** A practical example would depend on the specific standard clause or formula shown in your current step.

**In your task:** Use this explanation to interpret the workspace output; it does not advance the calculation or request new inputs.`
}
