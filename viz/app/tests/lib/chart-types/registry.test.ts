import { describe, it, expect } from 'vitest';
import { CHART_TYPES, isPresetType } from '@/lib/chart-types/registry';

describe('chart-types registry', () => {
  it('registers 5 preset types', () => {
    expect(new Set(CHART_TYPES)).toEqual(new Set(['line', 'bar', 'kpi', 'table', 'pie']));
  });
  it('isPresetType returns correctly', () => {
    expect(isPresetType('line')).toBe(true);
    expect(isPresetType('vega')).toBe(false);
  });
});
