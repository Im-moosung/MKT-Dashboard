import { notFound, redirect } from 'next/navigation';
import { auth } from '@/lib/auth/options';
import { getDashboard, listChartsByDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

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

  return (
    <main className="container mx-auto max-w-6xl p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{dashboard.title}</h1>
        {dashboard.description && (
          <p className="mt-1 text-sm text-muted-foreground">{dashboard.description}</p>
        )}
      </div>
      {/* Task 5: React Grid Layout + chart components will be added here */}
      {charts.length === 0 ? (
        <p className="text-muted-foreground">차트가 없습니다. 차트를 추가해 주세요.</p>
      ) : (
        <p className="text-muted-foreground">{charts.length}개 차트 (Task 5에서 그리드 렌더 추가 예정)</p>
      )}
    </main>
  );
}
