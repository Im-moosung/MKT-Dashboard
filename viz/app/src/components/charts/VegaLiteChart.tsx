'use client';
import { useEffect, useRef } from 'react';
import type { VegaChartConfig } from '@/lib/chart-types/registry';

export function VegaLiteChart({ data, config }: { data: Record<string, unknown>[]; config: VegaChartConfig }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    import('vega-embed').then(({ default: embed }) => {
      const spec = { ...config.spec, ...(data.length > 0 ? { data: { values: data } } : {}) };
      // vega-embed accepts VisualizationSpec which is a complex union; cast here is safe
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if (ref.current) embed(ref.current, spec as any, { actions: false });
    });
  }, [data, config]);
  return <div ref={ref} data-chart="vega" className="w-full" />;
}
