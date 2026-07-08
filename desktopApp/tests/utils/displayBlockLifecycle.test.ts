import { describe, expect, it } from 'vitest'

import {
  inferDisplayChannel,
  inferDisplayLifecycle,
  inferDisplayRole,
} from '@/utils/displayBlockLifecycle'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

describe('displayBlockLifecycle', () => {
  it('classifies fresh blocks with lifecycle metadata', () => {
    const preview: DisplayOutputBlock = {
      id: 'path-preview-equation-304.1.1-a',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'preview',
      display_channel: 'current_equation_preview',
      content: 't_m = t + c',
      display: 't_m = t + c',
    }

    expect(inferDisplayLifecycle(preview)).toBe('preview')
    expect(inferDisplayChannel(preview)).toBe('current_equation_preview')
    expect(inferDisplayRole(preview)).toBe('preview')
  })

  it('classifies legacy blocks without lifecycle metadata', () => {
    const legacyActivation: DisplayOutputBlock = {
      id: 'node-activation-equation-B313-304.1.1-0',
      type: 'equation',
      content: 't_m = t + c',
      display: 't_m = t + c',
    }
    const legacyPreview: DisplayOutputBlock = {
      id: 'path-preview-equation-304.1.2-a',
      type: 'equation',
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }

    expect(inferDisplayLifecycle(legacyActivation)).toBe('preview')
    expect(inferDisplayLifecycle(legacyPreview)).toBe('preview')
  })

  it('keeps durable explanatory intro blocks durable', () => {
    const explanation: DisplayOutputBlock = {
      id: 'preview-intro',
      type: 'text',
      content: 'The minimum required wall thickness shall be computed.',
    }

    expect(inferDisplayLifecycle(explanation)).toBe('durable')
  })

  it('classifies path-preview-intro as preview context only', () => {
    const intro: DisplayOutputBlock = {
      id: 'path-preview-intro-304.1.2-a',
      type: 'text',
      content: 'Minimum required wall thickness based on',
    }

    expect(inferDisplayLifecycle(intro)).toBe('preview')
    expect(inferDisplayChannel(intro)).toBe('current_node_intro')
  })

  it('classifies substituted and derived equation results as durable', () => {
    const substituted: DisplayOutputBlock = {
      id: 'path-calculation-substituted-equation',
      type: 'equation',
      lifecycle: 'durable',
      display_role: 'substituted',
      equation_node_id: 'asme-b313-304-1-2-eq-3a',
      content: 't = 1.23 mm',
      display: 't = 1.23 mm',
    }
    const derived: DisplayOutputBlock = {
      id: 'minimum-thickness-equation',
      type: 'equation',
      lifecycle: 'durable',
      display_role: 'derived',
      equation_node_id: 'asme-b313-304-1-1-eq-2',
      content: 't_m = 2.252',
      display: 't_m = 2.252',
    }

    expect(inferDisplayLifecycle(substituted)).toBe('durable')
    expect(inferDisplayLifecycle(derived)).toBe('durable')
  })
})
