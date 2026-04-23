'use client';
import { useState, useEffect, useCallback } from 'react';
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

export function SharedDashboardClient({
  dashboard,
  initialCharts,
}: {
  dashboard: Dashboard;
  initialCharts: ChartRow[];
}) {
  const [dataByChart, setData] = useState<Record<string, Record<string, unknown>[]>>({});

  const loadAllChartData = useCallback(async (chartList: ChartRow[]) => {
    const entries = await Promise.all(
      chartList.map(async (c) => {
        try {
          const { data } = await loadCubeData(c.cubeQueryJson);
          return [c.id, data] as const;
        } catch {
          return [c.id, []] as const;
        }
      }),
    );
    setData(Object.fromEntries(entries));
  }, []);

  useEffect(() => {
    loadAllChartData(initialCharts);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b px-6 py-3 flex items-center justify-between bg-background/80 backdrop-blur">
        <h1 className="text-xl font-bold">{dashboard.title}</h1>
        <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">읽기 전용</span>
      </header>
      <main className="p-6">
        {initialCharts.length === 0 ? (
          <p className="text-muted-foreground">차트가 없습니다.</p>
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
              // read-only: no-op
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
    </div>
  );
}
