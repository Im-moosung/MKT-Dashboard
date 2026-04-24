import { describe, it, expect, afterAll } from 'vitest';
import { inArray } from 'drizzle-orm';
import { getCurrentMonthBqUsage, recordBqQuery } from '@/lib/db/bq-query-log';
import { db } from '@/lib/db/client';
import { bqQueryLog } from '@/lib/db/schema';

describe('bq query log', () => {
  const hashes = ['test-bq-april-1', 'test-bq-april-2', 'test-bq-march-1'];

  afterAll(async () => {
    await db.delete(bqQueryLog).where(inArray(bqQueryLog.queryHash, hashes));
  });

  it('sums app-mediated query bytes only inside the current UTC month', async () => {
    const now = new Date('2026-04-24T02:00:00Z');
    const before = await getCurrentMonthBqUsage(now);

    await recordBqQuery({
      queryHash: hashes[0],
      estimatedBytes: 100,
      status: 'ok',
      createdAt: new Date('2026-04-01T00:00:00Z'),
    });
    await recordBqQuery({
      queryHash: hashes[1],
      estimatedBytes: 200,
      actualBytes: 150,
      status: 'error',
      createdAt: new Date('2026-04-30T23:59:59Z'),
    });
    await recordBqQuery({
      queryHash: hashes[2],
      estimatedBytes: 999,
      status: 'ok',
      createdAt: new Date('2026-03-31T23:59:59Z'),
    });

    const after = await getCurrentMonthBqUsage(now);
    expect(after.usedBytes - before.usedBytes).toBe(250);
  });
});
