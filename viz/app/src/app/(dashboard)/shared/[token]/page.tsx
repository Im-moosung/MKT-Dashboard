import { notFound, redirect } from 'next/navigation';
import { auth } from '@/lib/auth/options';
import { listChartsByDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { shareTokens, dashboards, users } from '@/lib/db/schema';
import { eq, and, isNull, gt } from 'drizzle-orm';
import { SharedDashboardClient } from './shared-client';

interface Props {
  params: Promise<{ token: string }>;
}

export default async function SharedDashboardPage({ params }: Props) {
  const { token } = await params;

  const session = await auth();
  if (!session?.user?.email) redirect('/login');

  const ALLOWED_DOMAIN = process.env.ALLOWED_EMAIL_DOMAIN ?? 'dstrict.com';
  if (!session.user.email.endsWith(`@${ALLOWED_DOMAIN}`)) redirect('/login');

  // Look up the share token
  const now = new Date();
  const rows = await db
    .select()
    .from(shareTokens)
    .where(
      and(
        eq(shareTokens.token, token),
        isNull(shareTokens.revokedAt),
      ),
    )
    .limit(1);

  if (!rows[0]) notFound();

  const shareRow = rows[0];

  // Check expiry if set
  if (shareRow.expiresAt && shareRow.expiresAt < now) {
    notFound();
  }

  // Fetch dashboard (no ownership check — token-based access)
  const dashboardRows = await db
    .select()
    .from(dashboards)
    .where(eq(dashboards.id, shareRow.dashboardId))
    .limit(1);

  if (!dashboardRows[0]) notFound();

  const dashboard = dashboardRows[0];
  const charts = await listChartsByDashboard(dashboard.id);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return <SharedDashboardClient dashboard={dashboard} initialCharts={charts as any[]} />;
}
