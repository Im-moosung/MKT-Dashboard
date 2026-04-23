'use client';
import type { PresetChartConfig } from '@/lib/chart-types/registry';
import { formatCurrency, formatNumber, formatPercent } from '@/lib/format';

function formatValue(val: unknown, fmt?: { y?: 'currency' | 'percent' | 'number' }): string {
  if (fmt?.y === 'currency') return formatCurrency(val);
  if (fmt?.y === 'percent') return formatPercent(val);
  return formatNumber(val);
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
