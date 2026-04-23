import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { db } from '@/lib/db/client';
import { users, chatMessages } from '@/lib/db/schema';
import { getDashboard } from '@/lib/db/queries';
import { eq, asc } from 'drizzle-orm';
import { parseUuid } from '@/lib/api/validation';

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
  const uuid = parseUuid(id);
  if (!uuid) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const dashboard = await getDashboard(uuid, user.id);
  if (!dashboard) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const messages = await db
    .select({
      id: chatMessages.id,
      role: chatMessages.role,
      content: chatMessages.content,
      createdAt: chatMessages.createdAt,
    })
    .from(chatMessages)
    .where(eq(chatMessages.dashboardId, uuid))
    .orderBy(asc(chatMessages.createdAt));

  return NextResponse.json({ messages });
}
