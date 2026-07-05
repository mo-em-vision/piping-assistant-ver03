import { describe, expect, it } from 'vitest'



import { withTaskQuery } from '@graph-explorer/utils/taskQuery'



describe('graph explorer task query', () => {

  it('includes explicit task id in query string', () => {

    expect(withTaskQuery({ taskId: 'task-123', params: { revision: 'rev-1' } })).toBe(

      '?revision=rev-1&task=task-123',

    )

  })



  it('includes session id alongside task id', () => {

    expect(withTaskQuery({ taskId: 'task-123', sessionId: 'project-456' })).toBe(

      '?task=task-123&session_id=project-456',

    )

  })

})

