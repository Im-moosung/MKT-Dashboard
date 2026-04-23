'use client';
import type { PresetChartConfig } from '@/lib/chart-types/registry';

function formatValue(val: unknown, fmt?: { y?: 'currency' | 'percent' | 'number' }): string {
  const n = Number(val);
  if (isNaN(n)) return String(val ?? '—');
  if (fmt?.y === 'currency') return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
  if (fmt?.y === 'percent') return `${n.toFixed(1)}%`;
  return new Intl.NumberFormat('ko-KR').format(n);
}

export function KPICard({ data, config }: { data: Record<string, unknown>[]; config: PresetChartConfig }) {
  const yField = Array.isArray(config.y) ? config.y[0] : config.y;
  const lastRow = data[data.length - 1];
  const value = lastRow && yField ? lastRow[yField] : undefined;

  return (
    <div data-chart="kpi" className="flex h-full w-full flex-col items-center justify-center gap-1">
      <span className="text-4xl font-bold tabular-nums">{formatValue(value, config.format)}</span>
      {yField && <span className="text-xs text-muted-foreground">{yField}</span>}
    </div>
  );
}
