import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { getDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users, shareTokens } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { parseUuid } from '@/lib/api/validation';
import crypto from 'crypto';

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const rows = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return rows[0] ?? null;
}

export async function POST(
  _: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const uuid = parseUuid(id);
  if (!uuid) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const dashboard = await getDashboard(uuid, user.id);
  if (!dashboard) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const token = crypto.randomBytes(32).toString('hex');

  await db.insert(shareTokens).values({
    dashboardId: uuid,
    token,
    createdBy: user.id,
  });

  const baseUrl = process.env.NEXTAUTH_URL ?? 'http://localhost:3000';
  const url = `${baseUrl}/shared/${token}`;

  return NextResponse.json({ token, url });
}
