import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { getCurrentMonthBqUsage } from '@/lib/db/bq-query-log';

export async function GET() {
  const session = await auth();
  if (!session?.user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const usage = await getCurrentMonthBqUsage();
  return NextResponse.json({ usage });
}
