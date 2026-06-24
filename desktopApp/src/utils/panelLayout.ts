export const MIN_PANEL_WIDTH = 200
export const MAX_LEFT_PANEL_WIDTH = 480
export const MIN_CENTER_PANEL_WIDTH = 280
export const DEFAULT_LEFT_WIDTH = 260
export const DEFAULT_RIGHT_WIDTH = 320
export const COLLAPSED_RAIL_WIDTH = 32
export const RESIZE_HANDLE_WIDTH = 4

export function clampLeftPanelWidth(width: number): number {
  return Math.min(MAX_LEFT_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, width))
}

export function clampRightPanelWidth(width: number, maxWidth: number): number {
  const effectiveMax = Math.max(MIN_PANEL_WIDTH, maxWidth)
  return Math.min(effectiveMax, Math.max(MIN_PANEL_WIDTH, width))
}

export function computeMaxRightPanelWidth({
  workspaceWidth,
  leftWidth,
  leftCollapsed,
  rightPanelVisible,
}: {
  workspaceWidth: number
  leftWidth: number
  leftCollapsed: boolean
  rightPanelVisible: boolean
}): number {
  if (!rightPanelVisible || workspaceWidth <= 0) {
    return MIN_PANEL_WIDTH
  }

  const leftOccupied = leftCollapsed ? COLLAPSED_RAIL_WIDTH : leftWidth
  const resizeHandles = leftCollapsed ? RESIZE_HANDLE_WIDTH : RESIZE_HANDLE_WIDTH * 2
  const availableForCenterAndRight = workspaceWidth - leftOccupied - resizeHandles

  return Math.max(MIN_PANEL_WIDTH, availableForCenterAndRight - MIN_CENTER_PANEL_WIDTH)
}
