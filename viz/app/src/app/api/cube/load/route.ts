import { NextRequest, NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { auth } from '@/lib/auth/options';

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const { query } = await req.json();

  const token = jwt.sign(
    {
      user_id: (session.user as { id?: string }).id ?? session.user.email,
      email: session.user.email,
    },
    process.env.CUBE_API_SECRET!,
    { algorithm: 'HS256', expiresIn: '5m' },
  );

  const r = await fetch(`${process.env.CUBE_API_URL}/load`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: token,
    },
    body: JSON.stringify({ query }),
  });

  if (!r.ok) {
    return NextResponse.json(
      { error: 'cube_failed', status: r.status, body: await r.text() },
      { status: 502 },
    );
  }

  const body = (await r.json()) as { data?: Record<string, unknown>[] };
  const data = body.data ?? [];
  return NextResponse.json({ data });
}
