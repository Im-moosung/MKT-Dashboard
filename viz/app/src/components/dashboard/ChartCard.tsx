'use client';
import { LineChart } from '@/components/charts/LineChart';
import { BarChart } from '@/components/charts/BarChart';
import { KPICard } from '@/components/charts/KPICard';
import { TableChart } from '@/components/charts/TableChart';
import { PieChart } from '@/components/charts/PieChart';
import { VegaLiteChart } from '@/components/charts/VegaLiteChart';
import type { ChartConfig } from '@/lib/chart-types/registry';

export function ChartCard({
  title,
  config,
  data,
}: {
  title: string;
  config: ChartConfig;
  data: Record<string, unknown>[];
}) {
  return (
    <div className="flex h-full w-full flex-col rounded border bg-card p-3">
      <div className="mb-2 text-sm font-semibold">{title}</div>
      <div className="flex-1 overflow-hidden">
        {config.type === 'line' && <LineChart data={data} config={config} />}
        {config.type === 'bar' && <BarChart data={data} config={config} />}
        {config.type === 'kpi' && <KPICard data={data} config={config} />}
        {config.type === 'table' && <TableChart data={data} config={config} />}
        {config.type === 'pie' && <PieChart data={data} config={config} />}
        {config.type === 'vega' && <VegaLiteChart data={data} config={config} />}
      </div>
    </div>
  );
}
