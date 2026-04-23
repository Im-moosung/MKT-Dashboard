import NextAuth from 'next-auth';
import Google from 'next-auth/providers/google';
import Credentials from 'next-auth/providers/credentials';

const ALLOWED_DOMAIN = process.env.ALLOWED_EMAIL_DOMAIN || 'dstrict.com';
const MOCK_AUTH = process.env.MOCK_AUTH === 'true';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const providers: any[] = [
  Google({
    clientId: process.env.GOOGLE_CLIENT_ID ?? 'mock-client-id',
    clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? 'mock-client-secret',
  }),
];

// TODO(oauth-pending): remove mock provider once real Google OAuth client is issued.
// Tracked in docs/status.md "CRITICAL 후속 작업".
if (MOCK_AUTH) {
  providers.push(
    Credentials({
      id: 'mock',
      name: 'Mock (OAuth 발급 전 임시)',
      credentials: { email: { label: 'Email', type: 'email' } },
      async authorize(credentials) {
        const email = String(credentials?.email ?? '').trim().toLowerCase();
        if (!email.endsWith(`@${ALLOWED_DOMAIN}`)) return null;
        return {
          id: `mock-${email}`,
          email,
          name: email.split('@')[0],
          image: null,
        };
      },
    }),
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  callbacks: {
    async signIn({ profile, account, user }) {
      // Mock path: authorize()가 이미 도메인 검증 완료.
      if (account?.provider === 'mock') {
        if (!user?.email) return false;
        const { upsertUserByGoogle } = await import('@/lib/db/queries');
        await upsertUserByGoogle({
          email: user.email,
          googleSub: user.id ?? `mock-${user.email}`,
          displayName: user.name ?? undefined,
        });
        return true;
      }
      // Google path.
      if (!profile?.email) return false;
      if (!profile.email.endsWith(`@${ALLOWED_DOMAIN}`)) return false;
      const { upsertUserByGoogle } = await import('@/lib/db/queries');
      await upsertUserByGoogle({
        email: profile.email,
        googleSub: (profile as { sub?: string }).sub!,
        displayName: profile.name ?? undefined,
        avatarUrl: (profile as { picture?: string }).picture ?? undefined,
      });
      return true;
    },
    async session({ session, token }) {
      if (session.user && token.sub) (session.user as { id?: string }).id = token.sub;
      return session;
    },
  },
  trustHost: true,
});
