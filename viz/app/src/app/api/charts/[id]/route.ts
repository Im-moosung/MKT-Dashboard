import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { z } from 'zod';
import { updateChart, deleteChart, getDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users, dashboardCharts } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const rows = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return rows[0] ?? null;
}

/** Fetch chart row and verify caller owns the parent dashboard. */
async function requireChartOwnership(chartId: string, userId: string) {
  const rows = await db
    .select()
    .from(dashboardCharts)
    .where(eq(dashboardCharts.id, chartId))
    .limit(1);
  const chart = rows[0];
  if (!chart) return null;
  const dashboard = await getDashboard(chart.dashboardId, userId);
  if (!dashboard) return null;
  return chart;
}

const patchChartSchema = z.object({
  title: z.string().min(1).max(255).optional(),
  cubeQueryJson: z.unknown().optional(),
  chartConfigJson: z.unknown().optional(),
  gridX: z.number().int().optional(),
  gridY: z.number().int().optional(),
  gridW: z.number().int().optional(),
  gridH: z.number().int().optional(),
});

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const chart = await requireChartOwnership(id, user.id);
  if (!chart) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const body = patchChartSchema.safeParse(await req.json());
  if (!body.success) return NextResponse.json({ error: 'bad_request', issues: body.error.issues }, { status: 400 });

  const updated = await updateChart(id, chart.dashboardId, body.data);
  if (!updated) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  return NextResponse.json({ chart: updated });
}

export async function DELETE(
  _: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const chart = await requireChartOwnership(id, user.id);
  if (!chart) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  await deleteChart(id, chart.dashboardId);
  return NextResponse.json({ ok: true });
}
