import { notFound, redirect } from 'next/navigation';
import { auth } from '@/lib/auth/options';
import { getDashboard, listChartsByDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { DashboardClient } from './dashboard-client';

interface Props {
  params: Promise<{ id: string }>;
}

export default async function DashboardDetailPage({ params }: Props) {
  const { id } = await params;
  const session = await auth();
  if (!session?.user?.email) redirect('/login');

  const [user] = await db
    .select()
    .from(users)
    .where(eq(users.email, session.user.email))
    .limit(1);

  if (!user) redirect('/login');

  const dashboard = await getDashboard(id, user.id);
  if (!dashboard) notFound();

  const charts = await listChartsByDashboard(id);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return <DashboardClient dashboard={dashboard} initialCharts={charts as any[]} />;
}
