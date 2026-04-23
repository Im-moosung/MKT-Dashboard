import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { z } from 'zod';
import { getDashboard, updateDashboard, deleteDashboard, listChartsByDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const rows = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return rows[0] ?? null;
}

export async function GET(
  _: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const d = await getDashboard(id, user.id);
  if (!d) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  const charts = await listChartsByDashboard(id);
  return NextResponse.json({ dashboard: d, charts });
}

const patchSchema = z.object({
  title: z.string().min(1).max(255).optional(),
  description: z.string().optional(),
});

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const body = patchSchema.safeParse(await req.json());
  if (!body.success) return NextResponse.json({ error: 'bad_request', issues: body.error.issues }, { status: 400 });
  const d = await updateDashboard(id, user.id, body.data);
  if (!d) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  return NextResponse.json({ dashboard: d });
}

export async function DELETE(
  _: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const d = await getDashboard(id, user.id);
  if (!d) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  await deleteDashboard(id, user.id);
  return NextResponse.json({ ok: true });
}
