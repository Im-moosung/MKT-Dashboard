'use client';
import { useEffect, useRef } from 'react';
import type { VegaChartConfig } from '@/lib/chart-types/registry';

export function VegaLiteChart({ data, config }: { data: Record<string, unknown>[]; config: VegaChartConfig }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    let result: { finalize: () => void } | null = null;
    let cancelled = false;
    import('vega-embed').then(({ default: embed }) => {
      if (cancelled || !ref.current) return;
      const spec = { ...config.spec, ...(data.length > 0 ? { data: { values: data } } : {}) };
      // vega-embed accepts VisualizationSpec which is a complex union; cast here is safe
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      embed(ref.current, spec as any, { actions: false })
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .then((r) => { if (!cancelled) result = r as any; else r.finalize(); })
        .catch((err) => console.error('[chart-embed] failed', err));
    });
    return () => {
      cancelled = true;
      result?.finalize();
    };
  }, [data, config]);
  return <div ref={ref} data-chart="vega" className="w-full" />;
}
