import { NextRequest, NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { auth } from '@/lib/auth/options';

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
    body: JSON.stringify({ query }),
  });

  if (!r.ok) {
    const upstreamBody = await r.text();
    console.error('[cube/load] upstream error', r.status, upstreamBody);
    return NextResponse.json({ error: 'cube_failed' }, { status: 502 });
  }

  const responseBody = (await r.json()) as { data?: Record<string, unknown>[] };
  const data = responseBody.data ?? [];
  return NextResponse.json({ data });
}
