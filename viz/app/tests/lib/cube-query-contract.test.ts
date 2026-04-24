import { describe, expect, it } from 'vitest';
import { validateCubeQueryContract } from '@/lib/cube-query-contract';

describe('validateCubeQueryContract', () => {
  it('rejects AdsCampaign queries without a reportDate time dimension', () => {
    const result = validateCubeQueryContract({
      measures: ['AdsCampaign.spend'],
      dimensions: ['AdsCampaign.branchId'],
      timeDimensions: [],
      filters: [],
    });

    expect(result).toEqual({
      ok: false,
      code: 'ads_campaign_report_date_required',
      message: expect.any(String),
    });
  });

  it('accepts AdsCampaign queries with a reportDate date range', () => {
    const result = validateCubeQueryContract({
      measures: ['AdsCampaign.spend'],
      dimensions: ['AdsCampaign.branchId'],
      timeDimensions: [
        { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' },
      ],
      filters: [],
    });

    expect(result).toEqual({ ok: true });
  });

  it('rejects Orders queries without an Orders.reportDate time dimension', () => {
    const result = validateCubeQueryContract({
      measures: ['Orders.orders'],
      dimensions: ['Orders.branchId'],
      timeDimensions: [],
      filters: [],
    });

    expect(result).toEqual({
      ok: false,
      code: 'orders_report_date_required',
      message: expect.any(String),
    });
  });

  it('rejects Surveys queries without a Surveys.reportDate time dimension', () => {
    const result = validateCubeQueryContract({
      measures: ['Surveys.responseCount'],
      dimensions: ['Surveys.branchId'],
      timeDimensions: [],
      filters: [],
    });

    expect(result).toEqual({
      ok: false,
      code: 'surveys_report_date_required',
      message: expect.any(String),
    });
  });
});
