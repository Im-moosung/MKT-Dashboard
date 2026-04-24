import { and, gte, lt, ne, sql } from 'drizzle-orm';
import { getBqUsageState, getMonthWindow } from '@/lib/bq-usage';
import { db } from './client';
import { bqQueryLog } from './schema';

export async function recordBqQuery(payload: {
  userId?: string | null;
  dashboardId?: string | null;
  queryHash: string;
  estimatedBytes: number;
  actualBytes?: number | null;
  status: 'ok' | 'error' | 'blocked';
  error?: string | null;
  createdAt?: Date;
}) {
  const [row] = await db
    .insert(bqQueryLog)
    .values({
      userId: payload.userId ?? null,
      dashboardId: payload.dashboardId ?? null,
      queryHash: payload.queryHash,
      estimatedBytes: payload.estimatedBytes,
      actualBytes: payload.actualBytes ?? null,
      status: payload.status,
      error: payload.error ?? null,
      createdAt: payload.createdAt ?? new Date(),
    })
    .returning();
  return row;
}

export async function getCurrentMonthBqUsage(now = new Date()) {
  const { start, end } = getMonthWindow(now);
  const [row] = await db
    .select({
      usedBytes: sql<number>`coalesce(sum(coalesce(${bqQueryLog.actualBytes}, ${bqQueryLog.estimatedBytes})), 0)`,
    })
    .from(bqQueryLog)
    .where(
      and(
        gte(bqQueryLog.createdAt, start),
        lt(bqQueryLog.createdAt, end),
        ne(bqQueryLog.status, 'blocked'),
      ),
    );

  return getBqUsageState(Number(row?.usedBytes ?? 0));
}
