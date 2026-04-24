import { describe, expect, it } from 'vitest';
import { buildPresetChartConfig, ensureRenderableChartConfig } from '@/lib/chart-config';

describe('buildPresetChartConfig', () => {
  it('builds a renderable bar chart config from a Cube query', () => {
    const config = buildPresetChartConfig(
      {
        measures: ['AdsCampaign.spend'],
        dimensions: ['AdsCampaign.branchId'],
        timeDimensions: [
          { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' },
        ],
        filters: [],
      },
      'bar',
    );

    expect(config).toEqual({
      type: 'bar',
      x: 'AdsCampaign.branchId',
      y: 'AdsCampaign.spend',
    });
  });

  it('prefers the time dimension for line chart x encoding', () => {
    const config = buildPresetChartConfig(
      {
        measures: ['AdsCampaign.spend'],
        dimensions: ['AdsCampaign.branchId'],
        timeDimensions: [
          { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' },
        ],
        filters: [],
      },
      'line',
    );

    expect(config).toEqual({
      type: 'line',
      x: 'AdsCampaign.reportDate',
      y: 'AdsCampaign.spend',
      series: 'AdsCampaign.branchId',
    });
  });

  it('repairs legacy preset configs that only persisted a chart type', () => {
    const config = ensureRenderableChartConfig(
      { type: 'bar' },
      {
        measures: ['AdsCampaign.spend'],
        dimensions: ['AdsCampaign.branchId'],
        timeDimensions: [
          { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' },
        ],
        filters: [],
      },
    );

    expect(config).toEqual({
      type: 'bar',
      x: 'AdsCampaign.branchId',
      y: 'AdsCampaign.spend',
    });
  });

  it('preserves explicit chart encodings', () => {
    const config = ensureRenderableChartConfig(
      { type: 'bar', x: 'Branch.branchName', y: 'AdsCampaign.spend' },
      {
        measures: ['AdsCampaign.spend'],
        dimensions: ['AdsCampaign.branchId'],
        timeDimensions: [],
        filters: [],
      },
    );

    expect(config).toEqual({ type: 'bar', x: 'Branch.branchName', y: 'AdsCampaign.spend' });
  });
});
