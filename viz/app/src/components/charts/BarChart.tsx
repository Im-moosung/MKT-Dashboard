'use client';
import { useEffect, useRef } from 'react';
import type { PresetChartConfig } from '@/lib/chart-types/registry';

export function BarChart({ data, config }: { data: Record<string, unknown>[]; config: PresetChartConfig }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    import('vega-embed').then(({ default: embed }) => {
      const spec: Record<string, unknown> = {
        $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
        width: 'container',
        height: 280,
        data: { values: data },
        mark: { type: 'bar' },
        encoding: {
          x: { field: config.x, type: 'ordinal', title: null },
          y: { field: Array.isArray(config.y) ? config.y[0] : config.y, type: 'quantitative', title: null },
          ...(config.series ? { color: { field: config.series, type: 'nominal' } } : {}),
        },
      };
      if (ref.current) embed(ref.current, spec, { actions: false });
    });
  }, [data, config]);
  return <div ref={ref} data-chart="bar" className="w-full" />;
}
