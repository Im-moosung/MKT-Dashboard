import { signIn } from '@/lib/auth/options';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const mockAuth = process.env.MOCK_AUTH === 'true';

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex w-96 flex-col gap-4 rounded-lg border p-8">
        <h1 className="text-2xl font-bold">MKT-Viz 로그인</h1>
        <p className="text-sm text-muted-foreground">@dstrict.com 계정으로 로그인</p>
        <form action={async () => { 'use server'; await signIn('google', { redirectTo: '/' }); }}>
          <Button type="submit" className="w-full">Google로 로그인</Button>
        </form>
        {mockAuth && (
          <>
            <div className="h-px bg-border" />
            <p className="text-xs text-muted-foreground">
              OAuth 발급 전 임시 로그인 (개발 전용)
            </p>
            <form
              action={async (fd: FormData) => {
                'use server';
                await signIn('mock', { email: fd.get('email'), redirectTo: '/' });
              }}
              className="flex flex-col gap-2"
            >
              <Input name="email" type="email" placeholder="you@dstrict.com" required />
              <Button type="submit" variant="outline" className="w-full">Mock 로그인</Button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
