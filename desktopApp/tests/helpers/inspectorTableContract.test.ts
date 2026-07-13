import { describe, expect, it } from 'vitest'

import {
  looksLikeRawJsonBlob,
} from './inspectorTableContract'

describe('inspectorTableContract', () => {
  it('detects planner json blobs and long json table dumps', () => {
    expect(looksLikeRawJsonBlob('8 bar')).toBe(false)
    expect(looksLikeRawJsonBlob('206.944 MPa (ASME B31.3 Table A-1)')).toBe(false)
    expect(looksLikeRawJsonBlob('{"GOAL-1": {"status": "blocked"}}')).toBe(true)
    expect(
      looksLikeRawJsonBlob(
        '{"engineering_plan": {"requirements": {"REQ-1": {"field": "material_grade"}}}}',
      ),
    ).toBe(true)
    expect(looksLikeRawJsonBlob(`{${'"x":'.repeat(80)}}`)).toBe(true)
  })
})
