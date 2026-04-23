export { auth as middleware } from '@/lib/auth/options';

export const config = {
  matcher: ['/((?!api/auth|_next/static|_next/image|login|favicon.ico).*)'],
};
