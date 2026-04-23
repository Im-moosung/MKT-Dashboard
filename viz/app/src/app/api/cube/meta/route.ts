import { NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { auth } from '@/lib/auth/options';

export async function GET() {
  const session = await auth();
  if (!session?.user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const token = jwt.sign(
    {
      user_id: (session.user as { id?: string }).id ?? session.user.email,
      email: session.user.email,
    },
    process.env.CUBE_API_SECRET!,
    { algorithm: 'HS256', expiresIn: '5m' },
  );

  const r = await fetch(`${process.env.CUBE_API_URL}/meta`, {
    headers: { authorization: token },
  });

  if (!r.ok) {
    const body = await r.text();
    console.error('[cube/meta] upstream error', r.status, body);
    return NextResponse.json({ error: 'cube_failed' }, { status: 502 });
  }

  const data = await r.json();
  return NextResponse.json(data);
}
