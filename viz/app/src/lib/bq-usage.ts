import { createHash } from 'node:crypto';

export const BQ_FREE_TIER_BYTES = 1024 ** 4;
const DEFAULT_QUERY_BYTES = 10 * 1024 ** 2;

export type BqUsageLevel = 'ok' | 'warning' | 'caution' | 'blocked';

export function getBqUsageState(usedBytes: number, budgetBytes = BQ_FREE_TIER_BYTES) {
  const ratio = budgetBytes > 0 ? usedBytes / budgetBytes : 1;
  const percent = Math.min(100, Math.round(ratio * 1000) / 10);
  const level: BqUsageLevel =
    ratio >= 0.95 ? 'blocked' : ratio >= 0.85 ? 'caution' : ratio >= 0.7 ? 'warning' : 'ok';

  return { usedBytes, budgetBytes, percent, level, blocked: level === 'blocked' };
}

export function getMonthWindow(now = new Date()) {
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1));
  return { start, end };
}

export function hashCubeQuery(query: unknown): string {
  return createHash('sha256').update(stableStringify(query)).digest('hex');
}

export function estimateCubeQueryBytes(query: unknown, baseBytes = DEFAULT_QUERY_BYTES): number {
  const daySpan = extractDateRangeDays(query) ?? 30;
  const rangeMultiplier = Math.max(1, Math.ceil(daySpan / 30));
  return baseBytes * rangeMultiplier;
}

function extractDateRangeDays(query: unknown): number | null {
  if (!query || typeof query !== 'object') return null;
  const timeDimensions = (query as { timeDimensions?: unknown }).timeDimensions;
  if (!Array.isArray(timeDimensions)) return null;

  for (const timeDimension of timeDimensions) {
    if (!timeDimension || typeof timeDimension !== 'object') continue;
    const dateRange = (timeDimension as { dateRange?: unknown }).dateRange;
    if (!Array.isArray(dateRange) || dateRange.length !== 2) continue;
    const [from, to] = dateRange;
    if (typeof from !== 'string' || typeof to !== 'string') continue;
    const fromDate = new Date(`${from}T00:00:00Z`);
    const toDate = new Date(`${to}T00:00:00Z`);
    if (Number.isNaN(fromDate.getTime()) || Number.isNaN(toDate.getTime())) continue;
    return Math.max(1, Math.floor((toDate.getTime() - fromDate.getTime()) / 86_400_000) + 1);
  }

  return null;
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  if (!value || typeof value !== 'object') return JSON.stringify(value);

  return `{${Object.keys(value)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stableStringify((value as Record<string, unknown>)[key])}`)
    .join(',')}}`;
}
