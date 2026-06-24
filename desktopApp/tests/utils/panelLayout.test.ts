import { describe, expect, it } from 'vitest'

import {
  clampLeftPanelWidth,
  clampRightPanelWidth,
  computeMaxRightPanelWidth,
  MAX_LEFT_PANEL_WIDTH,
  MIN_CENTER_PANEL_WIDTH,
  MIN_PANEL_WIDTH,
} from '@/utils/panelLayout'

describe('panelLayout', () => {
  it('keeps the left panel within its fixed maximum', () => {
    expect(clampLeftPanelWidth(600)).toBe(MAX_LEFT_PANEL_WIDTH)
    expect(clampLeftPanelWidth(120)).toBe(MIN_PANEL_WIDTH)
  })

  it('lets the right panel grow up to the center panel fully extended width', () => {
    const workspaceWidth = 1400
    const leftWidth = 260
    const maxRight = computeMaxRightPanelWidth({
      workspaceWidth,
      leftWidth,
      leftCollapsed: false,
      rightPanelVisible: true,
    })

    const centerWhenRightIsMin =
      workspaceWidth - leftWidth - 8 - MIN_PANEL_WIDTH

    expect(maxRight).toBe(workspaceWidth - leftWidth - 8 - MIN_CENTER_PANEL_WIDTH)
    expect(maxRight).toBeGreaterThan(480)
    expect(centerWhenRightIsMin - MIN_PANEL_WIDTH).toBeLessThanOrEqual(maxRight)
  })

  it('clamps the right panel to the computed maximum', () => {
    expect(clampRightPanelWidth(900, 700)).toBe(700)
    expect(clampRightPanelWidth(120, 700)).toBe(MIN_PANEL_WIDTH)
  })
})
