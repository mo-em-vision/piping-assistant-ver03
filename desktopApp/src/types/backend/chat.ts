export type ChatRole = 'user' | 'assistant'

export type ChatSourceKind = 'node' | 'table' | 'lookup_result'

export interface ChatSource {
  kind: ChatSourceKind
  id: string
  label: string
  standard?: string
  paragraph?: string
  node_id?: string
  table_id?: string
}

export interface ChatMessageDto {
  id: string
  role: ChatRole
  content: string
  timestamp: string
  status?: string | null
  task_id?: string | null
  sources?: ChatSource[]
}

export interface ChatContextDto {
  task_id?: string | null
  workflow_id?: string | null
  status?: string | null
  current_step_id?: string | null
  active_nodes?: string[]
  missing_inputs?: string[]
  output_count?: number
}

export interface ChatResponseDto {
  status: string
  message?: string | null
  question?: string | null
  task_id?: string | null
  required_by?: string | null
  data?: Record<string, unknown>
}

export interface ChatListResponse {
  session_id: string
  messages: ChatMessageDto[]
}

export interface ChatSendResponse {
  session_id: string
  user_message: ChatMessageDto
  assistant_message: ChatMessageDto
  response: ChatResponseDto
  context: ChatContextDto
  task_state: import('@/types/backend/api').TaskStateDto | null
}

export interface SendChatPayload {
  message: string
  task_id?: string
  display_message?: string
  mode?: 'workflow' | 'selection_explain' | 'task_assist'
}
