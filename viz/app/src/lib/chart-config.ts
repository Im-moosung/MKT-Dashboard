import {
  isPresetType,
  type ChartConfig,
  type PresetChartConfig,
  type PresetChartType,
} from '@/lib/chart-types/registry';

export interface CubeQueryForChartConfig {
  measures?: string[];
  dimensions?: string[];
  timeDimensions?: { dimension?: string; granularity?: string; dateRange?: string | string[] }[];
  filters?: unknown[];
}

export function buildPresetChartConfig(
  cubeQuery: CubeQueryForChartConfig,
  chartType: PresetChartType,
): ChartConfig {
  const measures = cubeQuery.measures ?? [];
  const dimensions = cubeQuery.dimensions ?? [];
  const firstMeasure = measures[0];
  const firstDimension = dimensions[0];
  const secondDimension = dimensions[1];
  const firstTimeDimension = cubeQuery.timeDimensions?.find((td) => td.dimension)?.dimension;

  const config: PresetChartConfig = { type: chartType };

  if (chartType === 'line') {
    assignIfDefined(config, 'x', firstTimeDimension ?? firstDimension);
    assignIfDefined(config, 'y', firstMeasure);
    if (firstTimeDimension && firstDimension) assignIfDefined(config, 'series', firstDimension);
    else assignIfDefined(config, 'series', secondDimension);
    return config;
  }

  if (chartType === 'kpi') {
    assignIfDefined(config, 'y', firstMeasure);
    return config;
  }

  if (chartType === 'table') {
    assignIfDefined(config, 'x', firstDimension ?? firstTimeDimension);
    assignIfDefined(config, 'y', measures.length > 1 ? measures : firstMeasure);
    return config;
  }

  assignIfDefined(config, 'x', firstDimension ?? firstTimeDimension);
  assignIfDefined(config, 'y', firstMeasure);
  assignIfDefined(config, 'series', secondDimension);
  return config;
}

export function ensureRenderableChartConfig(
  config: unknown,
  cubeQuery: CubeQueryForChartConfig,
): ChartConfig {
  if (!config || typeof config !== 'object') return buildPresetChartConfig(cubeQuery, 'line');

  const rec = config as Record<string, unknown>;
  if (rec.type === 'vega') return config as ChartConfig;
  if (typeof rec.type !== 'string' || !isPresetType(rec.type)) {
    return buildPresetChartConfig(cubeQuery, 'line');
  }

  const preset = config as PresetChartConfig;
  if (hasRenderableEncoding(preset)) return preset;
  return buildPresetChartConfig(cubeQuery, rec.type);
}

function hasRenderableEncoding(config: PresetChartConfig): boolean {
  if (config.type === 'table') return true;
  if (config.type === 'kpi') return Boolean(config.y);
  return Boolean(config.x && config.y);
}

function assignIfDefined<K extends keyof PresetChartConfig>(
  config: PresetChartConfig,
  key: K,
  value: PresetChartConfig[K] | undefined,
) {
  if (value !== undefined) config[key] = value;
}
