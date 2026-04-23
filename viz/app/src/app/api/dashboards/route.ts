import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { z } from 'zod';
import { createDashboard, listDashboards } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const rows = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return rows[0] ?? null;
}

const createSchema = z.object({
  title: z.string().min(1).max(255),
  description: z.string().optional(),
});

export async function GET() {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const list = await listDashboards(user.id);
  return NextResponse.json({ dashboards: list });
}

export async function POST(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const body = createSchema.safeParse(await req.json());
  if (!body.success) return NextResponse.json({ error: 'bad_request', issues: body.error.issues }, { status: 400 });
  const d = await createDashboard({ ownerId: user.id, ...body.data });
  return NextResponse.json({ dashboard: d }, { status: 201 });
}
