export const CHART_TYPES = ['line', 'bar', 'kpi', 'table', 'pie'] as const;
export type PresetChartType = typeof CHART_TYPES[number];

export function isPresetType(t: string): t is PresetChartType {
  return (CHART_TYPES as readonly string[]).includes(t);
}

export interface PresetChartConfig {
  type: PresetChartType;
  x?: string;
  y?: string | string[];
  series?: string;
  title?: string;
  format?: { y?: 'currency' | 'percent' | 'number' };
}

export interface VegaChartConfig {
  type: 'vega';
  spec: Record<string, unknown>;
  title?: string;
}

export type ChartConfig = PresetChartConfig | VegaChartConfig;
