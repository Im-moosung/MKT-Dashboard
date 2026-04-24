import { z } from 'zod';
import { GLOSSARY_KO } from '../prompts/glossary';
import { CHART_CREATE_INSTRUCTIONS } from '../prompts/chart-create';

export const ChartResponseSchema = z.object({
  cubeQuery: z.record(z.string(), z.unknown()),
  chartConfig: z.discriminatedUnion('type', [
    z.object({
      type: z.enum(['line', 'bar', 'kpi', 'table', 'pie']),
      x: z.string().optional(),
      y: z.union([z.string(), z.array(z.string())]).optional(),
      series: z.string().optional(),
      title: z.string().optional(),
      format: z.record(z.string(), z.string()).optional(),
    }),
    z.object({
      type: z.literal('vega'),
      spec: z.record(z.string(), z.unknown()),
      title: z.string().optional(),
    }),
  ]),
  title: z.string(),
});

export type ChartResponse = z.infer<typeof ChartResponseSchema>;

export type Usage = {
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens?: number;
};

export type CallResult = { response: ChartResponse; usage: Usage };

export type ProviderKind = 'openai' | 'claude' | 'mock';

export type ResolvedProvider = {
  provider: ProviderKind;
  model: string;
  slug: string;
};

const DEFAULT_PROVIDER: ProviderKind = 'openai';
const DEFAULT_MODEL: Record<ProviderKind, string> = {
  openai: 'gpt-5-nano',
  claude: 'claude-sonnet-4-6',
  mock: 'fixture',
};

function isMockEnv(): boolean {
  return process.env.MOCK_AI === 'true' || process.env.MOCK_CLAUDE === 'true';
}

export function resolveAiProvider(): ResolvedProvider {
  if (isMockEnv()) {
    const model = DEFAULT_MODEL.mock;
    return { provider: 'mock', model, slug: `mock:${model}` };
  }
  const raw = (process.env.AI_PROVIDER ?? DEFAULT_PROVIDER).toLowerCase();
  const provider: ProviderKind = raw === 'claude' ? 'claude' : raw === 'openai' ? 'openai' : DEFAULT_PROVIDER;
  const model = process.env.AI_MODEL?.trim() || DEFAULT_MODEL[provider];
  return { provider, model, slug: `${provider}:${model}` };
}

// W1/W2 local-smoke fixture. Targets cubes that round-trip against the current
// BigQuery mart (AdsCampaign AMNY/DSTX partial_real + Branch dim) so the full
// pipeline — provider → Cube /load → persist → chat — runs without any API key.
const MOCK_RESPONSE: ChartResponse = ChartResponseSchema.parse({
  cubeQuery: {
    measures: ['AdsCampaign.spend'],
    dimensions: ['Branch.branchName', 'AdsCampaign.sourceTier'],
    timeDimensions: [
      { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' },
    ],
    filters: [
      { member: 'AdsCampaign.branchId', operator: 'equals', values: ['AMNY', 'DSTX'] },
    ],
  },
  chartConfig: {
    type: 'bar',
    x: 'Branch.branchName',
    y: 'AdsCampaign.spend',
    series: 'AdsCampaign.sourceTier',
    title: '[MOCK] AMNY/DSTX 광고 스펜드',
  },
  title: '[MOCK] AMNY/DSTX 광고 스펜드',
});

function mockCall(): CallResult {
  return { response: MOCK_RESPONSE, usage: { input_tokens: 0, output_tokens: 0 } };
}

// JSON schema mirror for OpenAI Responses structured output. Kept permissive
// (strict: false) because Cube query + vega spec shapes are open-ended; Zod
// validates the final payload post-hoc.
const CHART_JSON_SCHEMA = {
  type: 'object',
  properties: {
    cubeQuery: { type: 'object' },
    chartConfig: { type: 'object' },
    title: { type: 'string' },
  },
  required: ['cubeQuery', 'chartConfig', 'title'],
};

async function openaiCall(prompt: string, cubeMetaJson: string, model: string): Promise<CallResult> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error('OPENAI_API_KEY is not configured');

  const systemText = [GLOSSARY_KO, `Cube meta:\n${cubeMetaJson}`, CHART_CREATE_INSTRUCTIONS].join('\n\n---\n\n');
  const body = {
    model,
    input: [
      { role: 'system', content: systemText },
      { role: 'user', content: prompt },
    ],
    text: {
      format: {
        type: 'json_schema',
        name: 'create_chart',
        schema: CHART_JSON_SCHEMA,
        strict: false,
      },
    },
    max_output_tokens: 2048,
  };

  const r = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${apiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`OpenAI responses ${r.status}: ${text.slice(0, 300)}`);
  }
  const data = (await r.json()) as {
    output_text?: string;
    output?: Array<{ content?: Array<{ text?: string }> }>;
    usage?: {
      input_tokens?: number;
      output_tokens?: number;
      input_tokens_details?: { cached_tokens?: number };
    };
  };

  const text =
    data.output_text ??
    data.output?.flatMap((o) => o.content ?? []).map((c) => c.text ?? '').join('') ??
    '';
  if (!text) throw new Error('OpenAI responses: empty output');

  const parsed = ChartResponseSchema.parse(JSON.parse(text));
  return {
    response: parsed,
    usage: {
      input_tokens: data.usage?.input_tokens ?? 0,
      output_tokens: data.usage?.output_tokens ?? 0,
      cache_read_input_tokens: data.usage?.input_tokens_details?.cached_tokens,
    },
  };
}

async function claudeCall(prompt: string, cubeMetaJson: string, model: string): Promise<CallResult> {
  const apiKey = process.env.CLAUDE_API_KEY ?? process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error('CLAUDE_API_KEY is not configured');

  // Lazy import so tests that never set AI_PROVIDER=claude do not pull the SDK.
  const { default: Anthropic } = await import('@anthropic-ai/sdk');
  const anthropic = new Anthropic({ apiKey });

  const r = await anthropic.messages.create({
    model,
    max_tokens: 2048,
    system: [
      { type: 'text', text: GLOSSARY_KO, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: `Cube meta:\n${cubeMetaJson}`, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: CHART_CREATE_INSTRUCTIONS, cache_control: { type: 'ephemeral' } },
    ] as Parameters<typeof anthropic.messages.create>[0]['system'],
    tools: [
      {
        name: 'create_chart',
        description: 'Emit a Cube query + chart config for the user request.',
        input_schema: {
          type: 'object',
          properties: {
            cubeQuery: { type: 'object' },
            chartConfig: { type: 'object' },
            title: { type: 'string' },
          },
          required: ['cubeQuery', 'chartConfig', 'title'],
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any,
    ],
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    tool_choice: { type: 'tool', name: 'create_chart' } as any,
    messages: [{ role: 'user', content: prompt }],
  });

  const block = r.content.find((b) => b.type === 'tool_use') as
    | { type: 'tool_use'; input: unknown }
    | undefined;
  if (!block) throw new Error('Claude response missing tool_use block');

  const parsed = ChartResponseSchema.parse(block.input);
  return {
    response: parsed,
    usage: {
      input_tokens: r.usage.input_tokens,
      output_tokens: r.usage.output_tokens,
      cache_read_input_tokens: (r.usage as { cache_read_input_tokens?: number }).cache_read_input_tokens,
    },
  };
}

export async function createChartFromPrompt(prompt: string, cubeMetaJson: string): Promise<CallResult> {
  const { provider, model } = resolveAiProvider();
  if (provider === 'mock') return mockCall();
  if (provider === 'claude') return claudeCall(prompt, cubeMetaJson, model);
  return openaiCall(prompt, cubeMetaJson, model);
}
