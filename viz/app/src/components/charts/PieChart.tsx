'use client';
import { useEffect, useRef } from 'react';
import type { PresetChartConfig } from '@/lib/chart-types/registry';

export function PieChart({ data, config }: { data: Record<string, unknown>[]; config: PresetChartConfig }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    import('vega-embed').then(({ default: embed }) => {
      const spec: Record<string, unknown> = {
        $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
        width: 280,
        height: 280,
        data: { values: data },
        mark: { type: 'arc' },
        encoding: {
          theta: { field: Array.isArray(config.y) ? config.y[0] : config.y, type: 'quantitative' },
          color: { field: config.x, type: 'nominal' },
        },
      };
      if (ref.current) embed(ref.current, spec, { actions: false });
    });
  }, [data, config]);
  return <div ref={ref} data-chart="pie" className="w-full" />;
}
