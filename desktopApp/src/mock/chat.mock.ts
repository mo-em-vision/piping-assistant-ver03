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
