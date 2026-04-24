import { describe, it, expect } from 'vitest';
import {
  BQ_FREE_TIER_BYTES,
  estimateCubeQueryBytes,
  getBqUsageState,
  getMonthWindow,
  hashCubeQuery,
} from '@/lib/bq-usage';

describe('bq usage guardrail', () => {
  it('uses a 1 TiB monthly free-tier budget and blocks at 95%', () => {
    expect(BQ_FREE_TIER_BYTES).toBe(1024 ** 4);

    const warning = getBqUsageState(0.7 * BQ_FREE_TIER_BYTES);
    expect(warning.level).toBe('warning');
    expect(warning.blocked).toBe(false);

    const caution = getBqUsageState(0.85 * BQ_FREE_TIER_BYTES);
    expect(caution.level).toBe('caution');
    expect(caution.blocked).toBe(false);

    const blocked = getBqUsageState(0.95 * BQ_FREE_TIER_BYTES);
    expect(blocked.level).toBe('blocked');
    expect(blocked.blocked).toBe(true);
  });

  it('calculates month windows in UTC', () => {
    const window = getMonthWindow(new Date('2026-04-24T02:00:00Z'));
    expect(window.start.toISOString()).toBe('2026-04-01T00:00:00.000Z');
    expect(window.end.toISOString()).toBe('2026-05-01T00:00:00.000Z');
  });

  it('hashes equivalent Cube queries stably', () => {
    const a = { dimensions: ['Branch.branchId'], measures: ['AdsCampaign.spend'] };
    const b = { measures: ['AdsCampaign.spend'], dimensions: ['Branch.branchId'] };
    expect(hashCubeQuery(a)).toBe(hashCubeQuery(b));
  });

  it('estimates longer date ranges as more expensive while staying deterministic', () => {
    const shortRange = {
      measures: ['AdsCampaign.spend'],
      timeDimensions: [{ dimension: 'AdsCampaign.reportDate', dateRange: ['2026-04-01', '2026-04-07'] }],
    };
    const longRange = {
      measures: ['AdsCampaign.spend'],
      timeDimensions: [{ dimension: 'AdsCampaign.reportDate', dateRange: ['2026-01-01', '2026-04-24'] }],
    };

    expect(estimateCubeQueryBytes(longRange)).toBeGreaterThan(estimateCubeQueryBytes(shortRange));
  });
});
