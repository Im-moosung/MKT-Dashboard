import { NextRequest, NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { auth } from '@/lib/auth/options';
import { estimateCubeQueryBytes, getBqUsageState, hashCubeQuery } from '@/lib/bq-usage';
import { getCurrentMonthBqUsage, recordBqQuery } from '@/lib/db/bq-query-log';
import { validateCubeQueryContract } from '@/lib/cube-query-contract';

const CubeQuerySchema = z
  .object({
    measures: z.array(z.string()).optional(),
    dimensions: z.array(z.string()).optional(),
    timeDimensions: z
      .array(
        z.object({
          dimension: z.string(),
          granularity: z.string().optional(),
          dateRange: z.union([z.string(), z.array(z.string())]).optional(),
        }),
      )
      .optional(),
    filters: z
      .array(
        z.object({
          member: z.string().optional(),
          and: z.array(z.any()).optional(),
          or: z.array(z.any()).optional(),
          operator: z.string().optional(),
          values: z.array(z.any()).optional(),
        }),
      )
      .optional(),
    order: z.any().optional(),
    limit: z.number().int().positive().max(10000).optional(),
    offset: z.number().int().nonnegative().optional(),
    segments: z.array(z.string()).optional(),
    timezone: z.string().optional(),
  })
  .passthrough();

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const body = await req.json();
  const query = body.query;
  if (query === undefined || query === null || typeof query !== 'object') {
    return NextResponse.json({ error: 'bad_request' }, { status: 400 });
  }

  const parsed = CubeQuerySchema.safeParse(query);
  if (!parsed.success) {
    return NextResponse.json({ error: 'bad_request', issues: parsed.error.issues }, { status: 400 });
  }

  const contract = validateCubeQueryContract(parsed.data);
  if (!contract.ok) {
    return NextResponse.json({ error: contract.code, message: contract.message }, { status: 400 });
  }

  const estimatedBytes = estimateCubeQueryBytes(parsed.data);
  const queryHash = hashCubeQuery(parsed.data);
  const userId = parseUuid((session.user as { id?: string }).id);
  const dashboardId = parseUuid(typeof body.dashboardId === 'string' ? body.dashboardId : undefined);
  const currentUsage = await getCurrentMonthBqUsage();
  const nextUsage = getBqUsageState(currentUsage.usedBytes + estimatedBytes);

  if (nextUsage.blocked) {
    await recordBqQuery({
      userId,
      dashboardId,
      queryHash,
      estimatedBytes,
      status: 'blocked',
      error: 'monthly_budget_threshold',
    }).catch((err: unknown) => console.error('[cube/load] bq_query_log blocked insert failed', err));
    return NextResponse.json({ error: 'bq_budget_exceeded', usage: nextUsage }, { status: 429 });
  }

  const secret = process.env.CUBE_API_SECRET;
  if (!secret) {
    console.error('[api/cube/load] CUBE_API_SECRET not configured');
    return NextResponse.json({ error: 'misconfigured' }, { status: 500 });
  }

  const token = jwt.sign(
    {
      user_id: (session.user as { id?: string }).id ?? session.user.email,
      email: session.user.email,
    },
    secret,
    { algorithm: 'HS256', expiresIn: '5m' },
  );

  const r = await fetch(`${process.env.CUBE_API_URL}/load`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: token,
    },
    body: JSON.stringify({ query: parsed.data }),
  });

  if (!r.ok) {
    const upstreamBody = await r.text();
    console.error('[cube/load] upstream error', r.status, upstreamBody);
    await recordBqQuery({
      userId,
      dashboardId,
      queryHash,
      estimatedBytes,
      status: 'error',
      error: `cube_failed:${r.status}`,
    }).catch((err: unknown) => console.error('[cube/load] bq_query_log error insert failed', err));
    return NextResponse.json({ error: 'cube_failed' }, { status: 502 });
  }

  const responseBody = (await r.json()) as { data?: Record<string, unknown>[] };
  const data = responseBody.data ?? [];
  await recordBqQuery({
    userId,
    dashboardId,
    queryHash,
    estimatedBytes,
    status: 'ok',
  }).catch((err: unknown) => console.error('[cube/load] bq_query_log ok insert failed', err));
  return NextResponse.json({ data, usage: nextUsage });
}

function parseUuid(value: string | undefined): string | null {
  if (!value) return null;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
    ? value
    : null;
}
