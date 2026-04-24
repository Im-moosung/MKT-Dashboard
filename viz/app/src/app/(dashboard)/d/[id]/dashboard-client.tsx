'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { DashboardGrid } from '@/components/dashboard/Grid';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { QueryBuilder } from '@/components/builder/QueryBuilder';
import { Preview } from '@/components/builder/Preview';
import { ChatPanel } from '@/components/ai-panel/ChatPanel';
import { loadCubeData } from '@/lib/cube-client';
import { buildPresetChartConfig, ensureRenderableChartConfig } from '@/lib/chart-config';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ShareDialog } from '@/components/dashboard/ShareDialog';
import type { BuilderState } from '@/components/builder/QueryBuilder';
import type { PresetChartType } from '@/lib/chart-types/registry';

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

interface BqUsage {
  percent: number;
  level: 'ok' | 'warning' | 'caution' | 'blocked';
}

const LAYOUT_DEBOUNCE_MS = 500;

export function DashboardClient({
  dashboard,
  initialCharts,
}: {
  dashboard: Dashboard;
  initialCharts: ChartRow[];
}) {
  const [charts, setCharts] = useState<ChartRow[]>(initialCharts);
  const [dataByChart, setData] = useState<Record<string, Record<string, unknown>[]>>({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'manual' | 'ai'>('manual');
  const [chartTitle, setChartTitle] = useState('새 차트');
  const [builderState, setBuilderState] = useState<BuilderState>({
    cubeQuery: { measures: [], dimensions: [], timeDimensions: [], filters: [] },
    chartType: 'line' as PresetChartType,
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [bqUsage, setBqUsage] = useState<BqUsage | null>(null);

  const layoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevLayoutRef = useRef<Map<string, { x: number; y: number; w: number; h: number }>>(
    new Map(initialCharts.map((c) => [c.id, { x: c.gridX, y: c.gridY, w: c.gridW, h: c.gridH }])),
  );

  const refreshBqUsage = useCallback(async () => {
    try {
      const r = await fetch('/api/bq-usage');
      if (!r.ok) return;
      const body = (await r.json()) as { usage?: BqUsage };
      if (body.usage) setBqUsage(body.usage);
    } catch {
      // Usage badge is informational; chart rendering should not depend on it.
    }
  }, []);

  // Load data for all charts
  const loadAllChartData = useCallback(async (chartList: ChartRow[]) => {
    const entries = await Promise.all(
      chartList.map(async (c) => {
        try {
          const { data } = await loadCubeData(c.cubeQueryJson, { dashboardId: dashboard.id });
          return [c.id, data] as const;
        } catch {
          return [c.id, []] as const;
        }
      }),
    );
    setData(Object.fromEntries(entries));
    refreshBqUsage();
  }, [dashboard.id, refreshBqUsage]);

  useEffect(() => {
    loadAllChartData(charts);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    return () => {
      if (layoutTimerRef.current) clearTimeout(layoutTimerRef.current);
    };
  }, []);

  const handleLayoutChange = useCallback(
    (layout: { i: string; x: number; y: number; w: number; h: number }[]) => {
      if (layoutTimerRef.current) clearTimeout(layoutTimerRef.current);

      layoutTimerRef.current = setTimeout(() => {
        const changed = layout.filter((item) => {
          const prev = prevLayoutRef.current.get(item.i);
          return (
            !prev ||
            prev.x !== item.x ||
            prev.y !== item.y ||
            prev.w !== item.w ||
            prev.h !== item.h
          );
        });

        if (changed.length === 0) return;

        for (const item of changed) {
          prevLayoutRef.current.set(item.i, { x: item.x, y: item.y, w: item.w, h: item.h });
          fetch(`/api/charts/${item.i}`, {
            method: 'PATCH',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ gridX: item.x, gridY: item.y, gridW: item.w, gridH: item.h }),
          }).catch((err) => console.error('[layout] PATCH failed', err));
        }
      }, LAYOUT_DEBOUNCE_MS);
    },
    [],
  );

  async function handleSave() {
    setSaveError(null);
    const measures = builderState.cubeQuery.measures ?? [];
    const dimensions = builderState.cubeQuery.dimensions ?? [];
    if (measures.length === 0 && dimensions.length === 0) {
      setSaveError('측정값 또는 차원을 하나 이상 선택해주세요.');
      return;
    }
    setSaving(true);
    try {
      const chartConfig = buildPresetChartConfig(builderState.cubeQuery, builderState.chartType);
      const body = {
        dashboardId: dashboard.id,
        title: chartTitle.trim() || '새 차트',
        cubeQueryJson: builderState.cubeQuery,
        chartConfigJson: chartConfig,
        source: 'manual' as const,
        promptHistoryJson: [],
        gridX: 0,
        gridY: 999, // append at bottom
        gridW: 6,
        gridH: 4,
      };

      const r = await fetch('/api/charts', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!r.ok) {
        const errBody = await r.json().catch(() => ({}));
        setSaveError('저장에 실패했습니다. ' + ((errBody as { error?: string }).error ?? ''));
        setSaving(false);
        return;
      }

      const { chart } = (await r.json()) as { chart: ChartRow };
      const newChart: ChartRow = {
        id: chart.id,
        title: chart.title,
        gridX: chart.gridX ?? 0,
        gridY: chart.gridY ?? 999,
        gridW: chart.gridW ?? 6,
        gridH: chart.gridH ?? 4,
        cubeQueryJson: builderState.cubeQuery,
        chartConfigJson: chartConfig,
      };

      setCharts((prev) => [...prev, newChart]);
      prevLayoutRef.current.set(newChart.id, {
        x: newChart.gridX,
        y: newChart.gridY,
        w: newChart.gridW,
        h: newChart.gridH,
      });

      // Load data for new chart
      try {
        const { data } = await loadCubeData(newChart.cubeQueryJson, { dashboardId: dashboard.id });
        setData((prev) => ({ ...prev, [newChart.id]: data }));
        refreshBqUsage();
      } catch {
        setData((prev) => ({ ...prev, [newChart.id]: [] }));
      }

      setDialogOpen(false);
      setChartTitle('새 차트');
      setBuilderState({
        cubeQuery: { measures: [], dimensions: [], timeDimensions: [], filters: [] },
        chartType: 'line',
      });
    } catch {
      setSaveError('저장에 실패했습니다. 네트워크 오류.');
    } finally {
      setSaving(false);
    }
  }

  function handleChartAdded(chart: ChartRow) {
    setCharts((prev) => [...prev, chart]);
    prevLayoutRef.current.set(chart.id, {
      x: chart.gridX,
      y: chart.gridY,
      w: chart.gridW,
      h: chart.gridH,
    });
    loadCubeData(chart.cubeQueryJson, { dashboardId: dashboard.id })
      .then(({ data }) => {
        setData((prev) => ({ ...prev, [chart.id]: data }));
        refreshBqUsage();
      })
      .catch(() => setData((prev) => ({ ...prev, [chart.id]: [] })));
  }

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <main className="flex-1 overflow-y-auto p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">{dashboard.title}</h1>
        <div className="flex items-center gap-2">
          {bqUsage && (
            <span
              className={`rounded border px-2 py-1 text-xs ${
                bqUsage.level === 'blocked'
                  ? 'border-destructive text-destructive'
                  : bqUsage.level === 'caution'
                    ? 'border-amber-500 text-amber-700'
                    : 'border-muted text-muted-foreground'
              }`}
              title="앱이 실행한 Cube/BigQuery 쿼리 기준의 근사 사용량입니다. BigQuery 콘솔에서 직접 실행한 쿼리는 포함하지 않습니다."
            >
              이번 달 BigQuery 사용량 · {bqUsage.percent}%
            </span>
          )}
          <ShareDialog dashboardId={dashboard.id} />
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) setSaveError(null); }}>
          <DialogTrigger render={<Button variant="default" />}>
            + 차트 추가
          </DialogTrigger>
          <DialogContent
            className="max-w-4xl w-full"
            aria-label="차트 추가"
          >
            <DialogHeader>
              <DialogTitle>차트 추가</DialogTitle>
            </DialogHeader>

            {/* Tabs */}
            <div className="flex gap-2 border-b mb-4">
              <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'manual'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
                onClick={() => setActiveTab('manual')}
              >
                수동 빌드
              </button>
              <button
                className="px-4 py-2 text-sm font-medium border-b-2 border-transparent text-muted-foreground cursor-not-allowed"
                disabled
                title="Task 7에서 활성화 예정"
              >
                AI로 만들기 (준비 중)
              </button>
            </div>

            {activeTab === 'manual' && (
              <div className="flex flex-col gap-4">
                {/* Title */}
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium w-16 shrink-0">제목</label>
                  <Input
                    value={chartTitle}
                    onChange={(e) => setChartTitle(e.target.value)}
                    placeholder="새 차트"
                    className="max-w-xs"
                  />
                </div>

                {/* Builder + Preview side by side */}
                <div className="grid grid-cols-2 gap-6 min-h-96">
                  <div className="overflow-y-auto">
                    <QueryBuilder
                      initial={builderState}
                      onChange={setBuilderState}
                    />
                  </div>
                  <div className="border rounded-lg p-3">
                    <Preview
                      cubeQuery={builderState.cubeQuery}
                      chartType={builderState.chartType}
                    />
                  </div>
                </div>
              </div>
            )}

            <DialogFooter>
              {saveError && (
                <p className="text-sm text-destructive mr-auto">{saveError}</p>
              )}
              <DialogClose render={<Button variant="outline" />}>취소</DialogClose>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? '저장 중…' : '저장'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {charts.length === 0 ? (
        <p className="text-muted-foreground">차트가 없습니다. 차트를 추가해 주세요.</p>
      ) : (
        <DashboardGrid
          charts={charts.map((c) => ({
            id: c.id,
            title: c.title,
            gridX: c.gridX,
            gridY: c.gridY,
            gridW: c.gridW,
            gridH: c.gridH,
          }))}
          onLayoutChange={handleLayoutChange}
          renderChart={(c) => {
            const chartRow = charts.find((x) => x.id === c.id);
            const config = ensureRenderableChartConfig(
              chartRow?.chartConfigJson,
              chartRow?.cubeQueryJson ?? {},
            );
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
      <ChatPanel dashboardId={dashboard.id} onChartAdded={handleChartAdded} />
    </div>
  );
}
