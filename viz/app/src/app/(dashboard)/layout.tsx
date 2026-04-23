import { auth } from '@/lib/auth/options';
import { redirect } from 'next/navigation';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect('/login');
  return <div className="min-h-screen bg-background">{children}</div>;
}
