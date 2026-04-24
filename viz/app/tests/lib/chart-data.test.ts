import { describe, expect, it } from 'vitest';
import { normalizeChartData } from '@/lib/chart-data';

describe('normalizeChartData', () => {
  it('coerces numeric string measures used by preset chart y encoding', () => {
    const data = [
      { 'AdsCampaign.branchId': 'AMNY', 'AdsCampaign.spend': '12578' },
      { 'AdsCampaign.branchId': 'DSTX', 'AdsCampaign.spend': '366.58629' },
    ];

    const normalized = normalizeChartData(data, {
      type: 'bar',
      x: 'AdsCampaign.branchId',
      y: 'AdsCampaign.spend',
    });

    expect(normalized).toEqual([
      { 'AdsCampaign.branchId': 'AMNY', 'AdsCampaign.spend': 12578 },
      { 'AdsCampaign.branchId': 'DSTX', 'AdsCampaign.spend': 366.58629 },
    ]);
  });

  it('leaves non-numeric strings unchanged', () => {
    const data = [{ label: 'AMNY', value: 'not-a-number' }];

    expect(normalizeChartData(data, { type: 'bar', x: 'label', y: 'value' })).toEqual(data);
  });
});
