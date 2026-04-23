'use client';
import { useState, useEffect } from 'react';
import { DashboardGrid } from '@/components/dashboard/Grid';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { loadCubeData } from '@/lib/cube-client';
import type { ChartConfig } from '@/lib/chart-types/registry';

interface ChartRow {
  id: string;
  title: string;
  gridX: number;
  gridY: number;
  gridW: number;
  gridH: number;
  cubeQueryJson: unknown;
  chartConfigJson: unknown;
}

interface Dashboard {
  id: string;
  title: string;
  description?: string | null;
}

export function DashboardClient({
  dashboard,
  initialCharts,
}: {
  dashboard: Dashboard;
  initialCharts: ChartRow[];
}) {
  const [dataByChart, setData] = useState<Record<string, Record<string, unknown>[]>>({});

  useEffect(() => {
    (async () => {
      const entries = await Promise.all(
        initialCharts.map(async (c) => {
          try {
            const { data } = await loadCubeData(c.cubeQueryJson);
            return [c.id, data] as const;
          } catch {
            return [c.id, []] as const;
          }
        }),
      );
      setData(Object.fromEntries(entries));
    })();
  }, [initialCharts]);

  return (
    <main className="p-6">
      <h1 className="mb-4 text-xl font-bold">{dashboard.title}</h1>
      {initialCharts.length === 0 ? (
        <p className="text-muted-foreground">차트가 없습니다. 차트를 추가해 주세요.</p>
      ) : (
        <DashboardGrid
          charts={initialCharts.map((c) => ({
            id: c.id,
            title: c.title,
            gridX: c.gridX,
            gridY: c.gridY,
            gridW: c.gridW,
            gridH: c.gridH,
          }))}
          onLayoutChange={() => {
            /* Task 6에서 저장 */
          }}
          renderChart={(c) => {
            const config =
              (initialCharts.find((x) => x.id === c.id)?.chartConfigJson as ChartConfig) ?? {
                type: 'line' as const,
              };
            return (
              <ChartCard
                title={c.title}
                config={config}
                data={dataByChart[c.id] ?? []}
              />
            );
          }}
        />
      )}
    </main>
  );
}
