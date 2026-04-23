import Link from 'next/link';
import { redirect } from 'next/navigation';
import { auth } from '@/lib/auth/options';
import { listDashboards, createDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default async function DashboardListPage() {
  const session = await auth();
  if (!session?.user?.email) redirect('/login');

  const [user] = await db
    .select()
    .from(users)
    .where(eq(users.email, session.user.email))
    .limit(1);

  if (!user) redirect('/login');

  const list = await listDashboards(user.id);

  async function createDashboardAction(formData: FormData) {
    'use server';
    const titleRaw = formData.get('title');
    const title =
      typeof titleRaw === 'string' && titleRaw.trim()
        ? titleRaw.trim()
        : '새 대시보드';

    const sess = await auth();
    if (!sess?.user?.email) redirect('/login');

    const rows = await db
      .select()
      .from(users)
      .where(eq(users.email, sess.user.email))
      .limit(1);

    if (!rows[0]) redirect('/login');

    const d = await createDashboard({ ownerId: rows[0].id, title });
    redirect(`/d/${d.id}`);
  }

  return (
    <main className="container mx-auto max-w-4xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">내 대시보드</h1>
        <form action={createDashboardAction}>
          <Button type="submit">+ 새 대시보드</Button>
        </form>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {list.length === 0 && (
          <p className="text-muted-foreground col-span-2">아직 대시보드가 없습니다.</p>
        )}
        {list.map((d) => (
          <Link key={d.id} href={`/d/${d.id}`}>
            <Card className="p-4 hover:border-primary transition-colors cursor-pointer">
              <h2 className="font-semibold">{d.title}</h2>
              <p className="text-xs text-muted-foreground">
                {new Date(d.updatedAt).toLocaleDateString('ko-KR')}
              </p>
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
