'use client';
import { LineChart } from '@/components/charts/LineChart';
import { BarChart } from '@/components/charts/BarChart';
import { KPICard } from '@/components/charts/KPICard';
import { TableChart } from '@/components/charts/TableChart';
import { PieChart } from '@/components/charts/PieChart';
import { VegaLiteChart } from '@/components/charts/VegaLiteChart';
import type { ChartConfig } from '@/lib/chart-types/registry';
import { normalizeChartData } from '@/lib/chart-data';

export function ChartCard({
  title,
  config,
  data,
}: {
  title: string;
  config: ChartConfig;
  data: Record<string, unknown>[];
}) {
  const chartData = normalizeChartData(data, config);

  return (
    <div className="flex h-full w-full flex-col rounded border bg-card p-3">
      <div className="mb-2 text-sm font-semibold">{title}</div>
      <div className="flex-1 overflow-hidden">
        {config.type === 'line' && <LineChart data={chartData} config={config} />}
        {config.type === 'bar' && <BarChart data={chartData} config={config} />}
        {config.type === 'kpi' && <KPICard data={chartData} config={config} />}
        {config.type === 'table' && <TableChart data={chartData} config={config} />}
        {config.type === 'pie' && <PieChart data={chartData} config={config} />}
        {config.type === 'vega' && <VegaLiteChart data={chartData} config={config} />}
      </div>
    </div>
  );
}
