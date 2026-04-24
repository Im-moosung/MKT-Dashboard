'use client';
import { useEffect, useRef } from 'react';
import type { PresetChartConfig } from '@/lib/chart-types/registry';
import { vegaField } from '@/lib/vega-fields';

export function LineChart({ data, config }: { data: Record<string, unknown>[]; config: PresetChartConfig }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    let result: { finalize: () => void } | null = null;
    let cancelled = false;
    import('vega-embed').then(({ default: embed }) => {
      if (cancelled || !ref.current) return;
      const spec: Record<string, unknown> = {
        $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
        width: 'container',
        height: 280,
        data: { values: data },
        mark: { type: 'line', point: true },
        encoding: {
          x: { field: vegaField(config.x), type: 'temporal', title: null },
          y: { field: vegaField(Array.isArray(config.y) ? config.y[0] : config.y), type: 'quantitative', title: null },
          ...(config.series ? { color: { field: vegaField(config.series), type: 'nominal' } } : {}),
        },
      };
      embed(ref.current, spec, { actions: false })
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .then((r) => { if (!cancelled) result = r as any; else r.finalize(); })
        .catch((err) => console.error('[chart-embed] failed', err));
    });
    return () => {
      cancelled = true;
      result?.finalize();
    };
  }, [data, config]);
  return <div ref={ref} data-chart="line" className="w-full" />;
}
