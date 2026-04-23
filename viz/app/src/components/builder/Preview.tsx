'use client';
import { useState, useEffect, useRef } from 'react';
import { ChartCard } from '@/components/dashboard/ChartCard';
import type { BuilderQuery } from './QueryBuilder';
import type { PresetChartType } from '@/lib/chart-types/registry';

const DEBOUNCE_MS = 300;

export function Preview({
  cubeQuery,
  chartType,
}: {
  cubeQuery: BuilderQuery;
  chartType: PresetChartType;
}) {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const hasMeasures = cubeQuery.measures.length > 0;
    const hasDimensions = cubeQuery.dimensions.length > 0;
    if (!hasMeasures && !hasDimensions) {
      setStatus('idle');
      return;
    }

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      setStatus('loading');
      try {
        const r = await fetch('/api/cube/load', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ query: cubeQuery }),
        });
        if (!r.ok) throw new Error(`${r.status}`);
        const json = (await r.json()) as { data?: Record<string, unknown>[] };
        setData(json.data ?? []);
        setStatus('idle');
      } catch {
        setStatus('error');
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [cubeQuery, chartType]);

  const config = { type: chartType } as const;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 text-xs font-medium text-muted-foreground">미리보기</div>
      {status === 'loading' && (
        <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
          불러오는 중…
        </div>
      )}
      {status === 'error' && (
        <div className="flex flex-1 items-center justify-center text-sm text-destructive">
          데이터를 불러오지 못했습니다.
        </div>
      )}
      {status === 'idle' && cubeQuery.measures.length === 0 && cubeQuery.dimensions.length === 0 && (
        <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
          측정값 또는 차원을 선택하면 미리보기가 표시됩니다.
        </div>
      )}
      {status === 'idle' && (cubeQuery.measures.length > 0 || cubeQuery.dimensions.length > 0) && (
        <div className="flex-1">
          <ChartCard title="미리보기" config={config} data={data} />
        </div>
      )}
    </div>
  );
}
