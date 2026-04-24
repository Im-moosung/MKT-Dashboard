import type { ChartConfig } from '@/lib/chart-types/registry';

export function normalizeChartData(
  data: Record<string, unknown>[],
  config: ChartConfig,
): Record<string, unknown>[] {
  if (config.type === 'vega') return data;

  const numericFields = new Set<string>();
  if (Array.isArray(config.y)) {
    for (const field of config.y) numericFields.add(field);
  } else if (config.y) {
    numericFields.add(config.y);
  }

  if (numericFields.size === 0) return data;

  return data.map((row) => {
    let changed = false;
    const next = { ...row };
    for (const field of numericFields) {
      const normalized = normalizeNumericValue(row[field]);
      if (normalized !== row[field]) {
        next[field] = normalized;
        changed = true;
      }
    }
    return changed ? next : row;
  });
}

function normalizeNumericValue(value: unknown): unknown {
  if (typeof value !== 'string') return value;
  const trimmed = value.trim();
  if (trimmed === '') return value;
  const numberValue = Number(trimmed);
  return Number.isFinite(numberValue) ? numberValue : value;
}
