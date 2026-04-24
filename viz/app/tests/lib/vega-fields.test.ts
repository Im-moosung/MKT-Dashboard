import { describe, expect, it } from 'vitest';
import { vegaField } from '@/lib/vega-fields';

describe('vegaField', () => {
  it('escapes Cube member dots so Vega-Lite treats them as literal field names', () => {
    expect(vegaField('AdsCampaign.spend')).toBe('AdsCampaign\\.spend');
    expect(vegaField('Branch.branchName')).toBe('Branch\\.branchName');
  });

  it('passes through empty or undefined fields', () => {
    expect(vegaField(undefined)).toBeUndefined();
    expect(vegaField('')).toBe('');
  });
});
