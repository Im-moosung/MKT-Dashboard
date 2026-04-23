import { describe, it, expect } from 'vitest';
import { ChartResponseSchema } from '@/lib/claude-client';

describe('ChartResponseSchema', () => {
  it('accepts valid chart response (line)', () => {
    const p = ChartResponseSchema.parse({
      cubeQuery: {
        measures: ['AdsCampaign.spend'],
        timeDimensions: [
          { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' },
        ],
      },
      chartConfig: {
        type: 'line',
        x: 'AdsCampaign.reportDate',
        y: 'AdsCampaign.spend',
        title: '최근 30일 스펜드',
      },
      title: '최근 30일 스펜드',
    });
    expect(p.chartConfig.type).toBe('line');
    expect(p.title).toBe('최근 30일 스펜드');
  });

  it('accepts valid chart response (vega)', () => {
    const p = ChartResponseSchema.parse({
      cubeQuery: { measures: ['AdsCampaign.spend'] },
      chartConfig: {
        type: 'vega',
        spec: { mark: 'bar' },
        title: '커스텀 차트',
      },
      title: '커스텀 차트',
    });
    expect(p.chartConfig.type).toBe('vega');
  });

  it('rejects invalid chart type', () => {
    expect(() =>
      ChartResponseSchema.parse({
        cubeQuery: {},
        chartConfig: { type: 'rocket' },
        title: 'x',
      }),
    ).toThrow();
  });

  it('rejects missing title', () => {
    expect(() =>
      ChartResponseSchema.parse({
        cubeQuery: {},
        chartConfig: { type: 'bar' },
      }),
    ).toThrow();
  });
});
