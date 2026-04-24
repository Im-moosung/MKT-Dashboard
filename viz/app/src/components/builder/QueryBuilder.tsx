'use client';
import { useState, useEffect } from 'react';
import { ChartTypePicker } from './ChartTypePicker';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { PresetChartType } from '@/lib/chart-types/registry';
import { sourceAwareTitle } from '@/lib/data-source-tiers';

interface CubeMeta {
  name: string;
  measures: { name: string; title: string }[];
  dimensions: { name: string; title: string; type?: string }[];
}

export interface BuilderQuery {
  measures: string[];
  dimensions: string[];
  timeDimensions: { dimension: string; granularity: string; dateRange: string }[];
  filters: { member: string; operator: string; values: string[] }[];
}

export interface BuilderState {
  cubeQuery: BuilderQuery;
  chartType: PresetChartType;
}

const OPERATORS = ['equals', 'notEquals', 'contains', 'gt', 'lt'] as const;
const GRANULARITIES = ['day', 'week', 'month', 'year'] as const;
const GRANULARITY_LABELS: Record<(typeof GRANULARITIES)[number], string> = {
  day: '일',
  week: '주',
  month: '월',
  year: '연',
};
const DATE_RANGES = [
  { label: '최근 7일', value: 'last 7 days' },
  { label: '최근 30일', value: 'last 30 days' },
  { label: '최근 90일', value: 'last 90 days' },
] as const;

interface FilterRow {
  id: string;
  member: string;
  operator: string;
  values: string[];
}

export function QueryBuilder({
  initial,
  onChange,
}: {
  initial?: Partial<BuilderState>;
  onChange: (state: BuilderState) => void;
}) {
  const [cubes, setCubes] = useState<CubeMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [measures, setMeasures] = useState<string[]>(initial?.cubeQuery?.measures ?? []);
  const [dimensions, setDimensions] = useState<string[]>(initial?.cubeQuery?.dimensions ?? []);
  const [timeDim, setTimeDim] = useState(initial?.cubeQuery?.timeDimensions?.[0]?.dimension ?? '');
  const [granularity, setGranularity] = useState(
    initial?.cubeQuery?.timeDimensions?.[0]?.granularity ?? 'day',
  );
  const [dateRange, setDateRange] = useState(
    initial?.cubeQuery?.timeDimensions?.[0]?.dateRange ?? 'last 30 days',
  );
  const [filters, setFilters] = useState<FilterRow[]>(
    (initial?.cubeQuery?.filters ?? []).map((f) => ({ id: crypto.randomUUID(), ...f })),
  );
  const [chartType, setChartType] = useState<PresetChartType>(initial?.chartType ?? 'line');

  useEffect(() => {
    fetch('/api/cube/meta')
      .then((r) => r.json())
      .then((d) => {
        if (d.cubes) setCubes(d.cubes as CubeMeta[]);
      })
      .catch(() => {/* meta unavailable — no-op */})
      .finally(() => setLoading(false));
  }, []);

  // Flat lists of all measures and dimensions across cubes
  const allMeasures = cubes.flatMap((c) => c.measures);
  const allDimensions = cubes.flatMap((c) => c.dimensions);
  const allTimeDimensions = allDimensions.filter((d) => d.type === 'time');
  const allMembers = [...allMeasures, ...allDimensions];

  function notify(
    m: string[],
    d: string[],
    td: string,
    g: string,
    dr: string,
    f: FilterRow[],
    ct: PresetChartType,
  ) {
    onChange({
      cubeQuery: {
        measures: m,
        dimensions: d,
        timeDimensions: td ? [{ dimension: td, granularity: g, dateRange: dr }] : [],
        filters: f.map(({ member, operator, values }) => ({ member, operator, values })),
      },
      chartType: ct,
    });
  }

  function toggleMeasure(name: string) {
    const next = measures.includes(name) ? measures.filter((x) => x !== name) : [...measures, name];
    setMeasures(next);
    notify(next, dimensions, timeDim, granularity, dateRange, filters, chartType);
  }

  function toggleDimension(name: string) {
    const next = dimensions.includes(name)
      ? dimensions.filter((x) => x !== name)
      : [...dimensions, name];
    setDimensions(next);
    notify(measures, next, timeDim, granularity, dateRange, filters, chartType);
  }

  function addFilter() {
    const next = [...filters, { id: crypto.randomUUID(), member: allMembers[0]?.name ?? '', operator: 'equals', values: [''] }];
    setFilters(next);
    notify(measures, dimensions, timeDim, granularity, dateRange, next, chartType);
  }

  function removeFilter(id: string) {
    const next = filters.filter((f) => f.id !== id);
    setFilters(next);
    notify(measures, dimensions, timeDim, granularity, dateRange, next, chartType);
  }

  function updateFilter(id: string, patch: Partial<Omit<FilterRow, 'id'>>) {
    const next = filters.map((f) => (f.id === id ? { ...f, ...patch } : f));
    setFilters(next);
    notify(measures, dimensions, timeDim, granularity, dateRange, next, chartType);
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground p-4">메타 정보 불러오는 중…</div>;
  }

  return (
    <div className="flex flex-col gap-4 text-sm">
      {/* Chart type */}
      <section>
        <div className="mb-1 font-medium">차트 타입</div>
        <ChartTypePicker
          value={chartType}
          onChange={(t) => {
            setChartType(t);
            notify(measures, dimensions, timeDim, granularity, dateRange, filters, t);
          }}
        />
      </section>

      {/* Measures */}
      <section>
        <div className="mb-1 font-medium">측정값</div>
        <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
          {allMeasures.map((m) => (
            <button
              key={m.name}
              onClick={() => toggleMeasure(m.name)}
              className={`rounded border px-2 py-0.5 text-xs transition-colors ${
                measures.includes(m.name)
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border hover:bg-muted'
              }`}
            >
              {sourceAwareTitle(m)}
            </button>
          ))}
          {allMeasures.length === 0 && (
            <span className="text-xs text-muted-foreground">측정값 없음 (Cube 연결 확인)</span>
          )}
        </div>
      </section>

      {/* Dimensions */}
      <section>
        <div className="mb-1 font-medium">차원</div>
        <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
          {allDimensions.map((d) => (
            <button
              key={d.name}
              onClick={() => toggleDimension(d.name)}
              className={`rounded border px-2 py-0.5 text-xs transition-colors ${
                dimensions.includes(d.name)
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border hover:bg-muted'
              }`}
            >
              {sourceAwareTitle(d)}
            </button>
          ))}
          {allDimensions.length === 0 && (
            <span className="text-xs text-muted-foreground">차원 없음</span>
          )}
        </div>
      </section>

      {/* Time dimension */}
      <section>
        <div className="mb-1 font-medium">기간</div>
        <div className="flex flex-wrap gap-2">
          <select
            aria-label="기간 필드"
            value={timeDim}
            onChange={(e) => {
              setTimeDim(e.target.value);
              notify(measures, dimensions, e.target.value, granularity, dateRange, filters, chartType);
            }}
            className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm"
          >
            <option value="">없음</option>
            {allTimeDimensions.map((d) => (
              <option key={d.name} value={d.name}>
                {d.title || d.name}
              </option>
            ))}
          </select>
          <select
            value={granularity}
            onChange={(e) => {
              setGranularity(e.target.value);
              notify(measures, dimensions, timeDim, e.target.value, dateRange, filters, chartType);
            }}
            className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm"
          >
            {GRANULARITIES.map((g) => (
              <option key={g} value={g}>{GRANULARITY_LABELS[g]}</option>
            ))}
          </select>
          <select
            value={dateRange}
            onChange={(e) => {
              setDateRange(e.target.value);
              notify(measures, dimensions, timeDim, granularity, e.target.value, filters, chartType);
            }}
            className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm"
          >
            {DATE_RANGES.map((dr) => (
              <option key={dr.value} value={dr.value}>{dr.label}</option>
            ))}
          </select>
        </div>
      </section>

      {/* Filters */}
      <section>
        <div className="mb-1 font-medium">필터</div>
        <div className="flex flex-col gap-2">
          {filters.map((f) => (
            <div key={f.id} className="flex items-center gap-2 flex-wrap">
              <select
                value={f.member}
                onChange={(e) => updateFilter(f.id, { member: e.target.value })}
                className="h-8 rounded-lg border border-input bg-transparent px-2 text-xs"
              >
                {allMembers.map((m) => (
                  <option key={m.name} value={m.name}>{sourceAwareTitle(m)}</option>
                ))}
              </select>
              <select
                value={f.operator}
                onChange={(e) => updateFilter(f.id, { operator: e.target.value })}
                className="h-8 rounded-lg border border-input bg-transparent px-2 text-xs"
              >
                {OPERATORS.map((op) => (
                  <option key={op} value={op}>{op}</option>
                ))}
              </select>
              <Input
                className="h-8 w-32 text-xs"
                value={f.values[0] ?? ''}
                onChange={(e) => updateFilter(f.id, { values: [e.target.value] })}
                placeholder="값"
              />
              <Button size="xs" variant="destructive" onClick={() => removeFilter(f.id)}>삭제</Button>
            </div>
          ))}
          <Button size="sm" variant="outline" onClick={addFilter} className="w-fit">
            + 필터 추가
          </Button>
        </div>
      </section>
    </div>
  );
}
