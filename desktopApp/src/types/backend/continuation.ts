export interface ContinuationSuggestionDto {
  id: string
  title: string
  description: string
}

export interface TaskContinuationSuggestionsDto {
  task_id: string
  workflow_id: string
  suggestions: ContinuationSuggestionDto[]
}
