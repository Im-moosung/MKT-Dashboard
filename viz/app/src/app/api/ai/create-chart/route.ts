import { NextRequest, NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { auth } from '@/lib/auth/options';
import { parseUuid } from '@/lib/api/validation';
import {
  createChartFromPrompt,
  resolveAiProvider,
  type ChartResponse,
} from '@/lib/claude-client';
import { db } from '@/lib/db/client';
import { users, aiCallLog, chatMessages } from '@/lib/db/schema';
import { getDashboard, createChart } from '@/lib/db/queries';
import { eq } from 'drizzle-orm';
import { estimateCubeQueryBytes, getBqUsageState, hashCubeQuery } from '@/lib/bq-usage';
import { getCurrentMonthBqUsage, recordBqQuery } from '@/lib/db/bq-query-log';
import { validateCubeQueryContract } from '@/lib/cube-query-contract';

const RequestBodySchema = z.object({
  prompt: z.string().min(1).max(2000),
  dashboardId: z.string().uuid(),
});

type StepError = { code: 'cube_failed' | 'claude_failed' | 'persist_failed' | 'bq_budget_exceeded'; cause: unknown };

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const rows = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return rows[0] ?? null;
}

function signCubeToken(userId: string, userEmail: string): string {
  const secret = process.env.CUBE_API_SECRET;
  if (!secret) throw new Error('CUBE_API_SECRET not configured');
  return jwt.sign(
    { user_id: userId, email: userEmail },
    secret,
    { algorithm: 'HS256', expiresIn: '5m' },
  );
}

async function fetchCubeMeta(userId: string, userEmail: string): Promise<string> {
  const token = signCubeToken(userId, userEmail);
  const r = await fetch(`${process.env.CUBE_API_URL}/meta`, { headers: { authorization: token } });
  if (!r.ok) throw new Error(`Cube meta failed: ${r.status}`);
  return r.text();
}

async function fetchCubeLoad(
  cubeQuery: Record<string, unknown>,
  userId: string,
  userEmail: string,
  dashboardId: string,
): Promise<Record<string, unknown>[]> {
  const contract = validateCubeQueryContract(cubeQuery);
  if (!contract.ok) throw new Error(contract.message);

  const estimatedBytes = estimateCubeQueryBytes(cubeQuery);
  const queryHash = hashCubeQuery(cubeQuery);
  const currentUsage = await getCurrentMonthBqUsage();
  const nextUsage = getBqUsageState(currentUsage.usedBytes + estimatedBytes);

  if (nextUsage.blocked) {
    await recordBqQuery({
      userId,
      dashboardId,
      queryHash,
      estimatedBytes,
      status: 'blocked',
      error: 'monthly_budget_threshold',
    }).catch((err: unknown) => console.error('[ai/create-chart] bq_query_log blocked insert failed', err));
    throw new Error('BigQuery monthly budget threshold exceeded');
  }

  const token = signCubeToken(userId, userEmail);
  const r = await fetch(`${process.env.CUBE_API_URL}/load`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: token },
    body: JSON.stringify({ query: cubeQuery }),
  });
  if (!r.ok) {
    await recordBqQuery({
      userId,
      dashboardId,
      queryHash,
      estimatedBytes,
      status: 'error',
      error: `cube_failed:${r.status}`,
    }).catch((err: unknown) => console.error('[ai/create-chart] bq_query_log error insert failed', err));
    throw new Error(`Cube load failed: ${r.status}`);
  }
  const body = (await r.json()) as { data?: Record<string, unknown>[] };
  await recordBqQuery({
    userId,
    dashboardId,
    queryHash,
    estimatedBytes,
    status: 'ok',
  }).catch((err: unknown) => console.error('[ai/create-chart] bq_query_log ok insert failed', err));
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

const FAILURE_MESSAGES: Record<StepError['code'], string> = {
  cube_failed: '데이터 조회에 실패했습니다. 잠시 후 다시 시도하거나 수동 빌더를 사용하세요.',
  claude_failed: 'AI가 응답하지 못했습니다. 다시 시도해 주세요.',
  persist_failed: '차트 저장에 실패했습니다. 다시 시도해 주세요.',
  bq_budget_exceeded: '이번 달 BigQuery 사용량이 안전 한도에 도달했습니다. 기간을 줄이거나 관리자에게 문의하세요.',
};

async function recordChat(
  dashId: string,
  userId: string,
  prompt: string,
  assistant: { content: string; chartId: string | null },
) {
  await db
    .insert(chatMessages)
    .values([
      { dashboardId: dashId, userId, role: 'user', content: prompt },
      {
        dashboardId: dashId,
        userId,
        role: 'assistant',
        content: assistant.content,
        toolCallsJson: { chartId: assistant.chartId },
      },
    ])
    .catch((err: unknown) => {
      console.error('[ai/create-chart] chat_messages insert failed', err);
    });
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

  // Ownership check — prevents IDOR
  const dashboard = await getDashboard(dashId, user.id);
  if (!dashboard) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const t0 = Date.now();
  let status: 'ok' | 'error' = 'error';
  let errorMsg: string | null = null;
  let inputTokens = 0;
  let outputTokens = 0;
  let cacheReadTokens = 0;
  const failureBox: { value: StepError | null } = { value: null };

  try {
    let metaJson: string;
    try {
      metaJson = await fetchCubeMeta(user.id, user.email);
    } catch (e) {
      failureBox.value = { code: 'cube_failed', cause: e };
      throw e;
    }

    let chart: ChartResponse;
    let usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number };
    try {
      const r = await callWithRetry(prompt, metaJson);
      chart = r.response;
      usage = r.usage;
    } catch (e) {
      failureBox.value = { code: 'claude_failed', cause: e };
      throw e;
    }

    inputTokens = usage.input_tokens;
    outputTokens = usage.output_tokens;
    cacheReadTokens = usage.cache_read_input_tokens ?? 0;

    let data: Record<string, unknown>[];
    try {
      data = await fetchCubeLoad(chart.cubeQuery as Record<string, unknown>, user.id, user.email, dashId);
    } catch (e) {
      failureBox.value = {
        code: e instanceof Error && e.message.includes('budget') ? 'bq_budget_exceeded' : 'cube_failed',
        cause: e,
      };
      throw e;
    }

    let persisted: Awaited<ReturnType<typeof createChart>>;
    try {
      persisted = await createChart({
        dashboardId: dashId,
        title: chart.title,
        cubeQueryJson: chart.cubeQuery,
        chartConfigJson: chart.chartConfig,
        source: 'ai',
        promptHistoryJson: [prompt],
        gridX: 0,
        gridY: 999,
        gridW: 6,
        gridH: 4,
      });
    } catch (e) {
      failureBox.value = { code: 'persist_failed', cause: e };
      throw e;
    }

    status = 'ok';

    await recordChat(dashId, user.id, prompt, {
      content: `✓ 차트 추가됨: ${persisted.title}`,
      chartId: persisted.id,
    });

    return NextResponse.json({ chart: persisted, response: chart, data });
  } catch (e) {
    errorMsg = e instanceof Error ? e.message : String(e);
    console.error('[ai/create-chart] error', failureBox.value?.code ?? 'unknown', errorMsg, e);

    const code = failureBox.value?.code ?? 'claude_failed';
    const userFacing = FAILURE_MESSAGES[code];

    await recordChat(dashId, user.id, prompt, { content: userFacing, chartId: null });

    const httpStatus = code === 'bq_budget_exceeded' ? 429 : code === 'persist_failed' ? 500 : 502;
    return NextResponse.json({ errorCode: code, error: userFacing }, { status: httpStatus });
  } finally {
    const latencyMs = Date.now() - t0;
    await db
      .insert(aiCallLog)
      .values({
        userId: user.id,
        dashboardId: dashId,
        endpoint: 'create-chart',
        model: resolveAiProvider().slug,
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
