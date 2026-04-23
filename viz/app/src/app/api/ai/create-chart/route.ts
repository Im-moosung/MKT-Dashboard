import { NextRequest, NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { auth } from '@/lib/auth/options';
import { parseUuid } from '@/lib/api/validation';
import { createChartFromPrompt, type ChartResponse } from '@/lib/claude-client';
import { db } from '@/lib/db/client';
import { users, aiCallLog, chatMessages } from '@/lib/db/schema';
import { getDashboard } from '@/lib/db/queries';
import { eq } from 'drizzle-orm';

const RequestBodySchema = z.object({
  prompt: z.string().min(1).max(2000),
  dashboardId: z.string().uuid(),
});

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const rows = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return rows[0] ?? null;
}

async function fetchCubeMeta(userId: string, userEmail: string): Promise<string> {
  const secret = process.env.CUBE_API_SECRET;
  if (!secret) throw new Error('CUBE_API_SECRET not configured');

  const token = jwt.sign(
    { user_id: userId, email: userEmail },
    secret,
    { algorithm: 'HS256', expiresIn: '5m' },
  );

  const r = await fetch(`${process.env.CUBE_API_URL}/meta`, {
    headers: { authorization: token },
  });
  if (!r.ok) throw new Error(`Cube meta failed: ${r.status}`);
  return r.text();
}

async function fetchCubeLoad(
  cubeQuery: Record<string, unknown>,
  userId: string,
  userEmail: string,
): Promise<Record<string, unknown>[]> {
  const secret = process.env.CUBE_API_SECRET;
  if (!secret) throw new Error('CUBE_API_SECRET not configured');

  const token = jwt.sign(
    { user_id: userId, email: userEmail },
    secret,
    { algorithm: 'HS256', expiresIn: '5m' },
  );

  const r = await fetch(`${process.env.CUBE_API_URL}/load`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: token },
    body: JSON.stringify({ query: cubeQuery }),
  });
  if (!r.ok) throw new Error(`Cube load failed: ${r.status}`);
  const body = (await r.json()) as { data?: Record<string, unknown>[] };
  return body.data ?? [];
}

async function callWithRetry(
  prompt: string,
  meta: string,
): Promise<{ response: ChartResponse; usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number } }> {
  try {
    return await createChartFromPrompt(prompt, meta);
  } catch (e) {
    if (!(e instanceof z.ZodError)) throw e;
    const retryPrompt = `${prompt}\n\nNote: Previous attempt produced invalid structured output. Please re-emit with strict schema compliance.`;
    return await createChartFromPrompt(retryPrompt, meta);
  }
}

export async function POST(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const bodyParsed = RequestBodySchema.safeParse(await req.json());
  if (!bodyParsed.success) {
    return NextResponse.json({ error: 'bad_request', issues: bodyParsed.error.issues }, { status: 400 });
  }
  const { prompt, dashboardId } = bodyParsed.data;

  const dashId = parseUuid(dashboardId);
  if (!dashId) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  // Ownership check — prevents IDOR (other users' dashboardId accepted)
  const dashboard = await getDashboard(dashId, user.id);
  if (!dashboard) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const t0 = Date.now();
  let status: 'ok' | 'error' = 'error';
  let errorMsg: string | null = null;
  let inputTokens = 0;
  let outputTokens = 0;
  let cacheReadTokens = 0;

  try {
    const metaJson = await fetchCubeMeta(user.id, user.email);
    const { response, usage } = await callWithRetry(prompt, metaJson);

    inputTokens = usage.input_tokens;
    outputTokens = usage.output_tokens;
    cacheReadTokens = usage.cache_read_input_tokens ?? 0;

    const data = await fetchCubeLoad(
      response.cubeQuery as Record<string, unknown>,
      user.id,
      user.email,
    );

    status = 'ok';

    // Insert chat_messages pair (user + assistant) — non-blocking, best-effort
    const chartTitle = response.title ?? '차트';
    await db
      .insert(chatMessages)
      .values([
        {
          dashboardId: dashId,
          userId: user.id,
          role: 'user',
          content: prompt,
        },
        {
          dashboardId: dashId,
          userId: user.id,
          role: 'assistant',
          content: `✓ 차트 추가됨: ${chartTitle}`,
          toolCallsJson: { chartId: null },
        },
      ])
      .catch((err: unknown) => {
        console.error('[ai/create-chart] chat_messages insert failed', err);
      });

    return NextResponse.json({ response, data });
  } catch (e) {
    errorMsg = e instanceof Error ? e.message : String(e);
    console.error('[ai/create-chart] error', errorMsg, e);

    // Best-effort: record the failed user message
    await db
      .insert(chatMessages)
      .values([
        {
          dashboardId: dashId,
          userId: user.id,
          role: 'user',
          content: prompt,
        },
        {
          dashboardId: dashId,
          userId: user.id,
          role: 'assistant',
          content: 'AI 응답 실패, 다시 시도해 주세요. 또는 수동 빌더를 사용하세요.',
        },
      ])
      .catch(() => {});

    return NextResponse.json({ error: 'AI 응답 실패, 다시 시도해 주세요. 또는 수동 빌더를 사용하세요.' }, { status: 502 });
  } finally {
    const latencyMs = Date.now() - t0;
    await db
      .insert(aiCallLog)
      .values({
        userId: user.id,
        dashboardId: dashId,
        endpoint: 'create-chart',
        model: 'claude-sonnet-4-6',
        inputTokens,
        outputTokens,
        cacheReadTokens,
        latencyMs,
        status,
        error: errorMsg,
      })
      .catch((err: unknown) => {
        console.error('[ai/create-chart] ai_call_log insert failed', err);
      });
  }
}
