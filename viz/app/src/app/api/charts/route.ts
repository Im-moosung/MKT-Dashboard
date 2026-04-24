import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { z } from 'zod';
import { createChart, getDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { validateCubeQueryContract } from '@/lib/cube-query-contract';

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const rows = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return rows[0] ?? null;
}

const createChartSchema = z.object({
  dashboardId: z.string().uuid(),
  title: z.string().min(1).max(255),
  cubeQueryJson: z.unknown(),
  chartConfigJson: z.unknown(),
  source: z.enum(['ai', 'manual', 'hybrid']).default('manual'),
  promptHistoryJson: z.unknown().optional(),
  gridX: z.number().int().optional(),
  gridY: z.number().int().optional(),
  gridW: z.number().int().optional(),
  gridH: z.number().int().optional(),
});

export async function POST(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const body = createChartSchema.safeParse(await req.json());
  if (!body.success) return NextResponse.json({ error: 'bad_request', issues: body.error.issues }, { status: 400 });

  // Verify caller owns the target dashboard (IDOR prevention).
  const dashboard = await getDashboard(body.data.dashboardId, user.id);
  if (!dashboard) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const contract = validateCubeQueryContract(body.data.cubeQueryJson);
  if (!contract.ok) {
    return NextResponse.json({ error: contract.code, message: contract.message }, { status: 400 });
  }

  const c = await createChart(body.data);
  return NextResponse.json({ chart: c }, { status: 201 });
}
