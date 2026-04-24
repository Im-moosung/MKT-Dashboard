import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import {
  ChartResponseSchema,
  createChartFromPrompt,
  resolveAiProvider,
} from '@/lib/claude-client';

describe('ChartResponseSchema', () => {
  it('accepts valid chart response (line)', () => {
    const p = ChartResponseSchema.parse({
      cubeQuery: {
        measures: ['AdsCampaign.spend'],
        timeDimensions: [
          { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' },
        ],
      },
      chartConfig: {
        type: 'line',
        x: 'AdsCampaign.reportDate',
        y: 'AdsCampaign.spend',
        title: '최근 30일 스펜드',
      },
      title: '최근 30일 스펜드',
    });
    expect(p.chartConfig.type).toBe('line');
    expect(p.title).toBe('최근 30일 스펜드');
  });

  it('accepts valid chart response (vega)', () => {
    const p = ChartResponseSchema.parse({
      cubeQuery: { measures: ['AdsCampaign.spend'] },
      chartConfig: {
        type: 'vega',
        spec: { mark: 'bar' },
        title: '커스텀 차트',
      },
      title: '커스텀 차트',
    });
    expect(p.chartConfig.type).toBe('vega');
  });

  it('rejects invalid chart type', () => {
    expect(() =>
      ChartResponseSchema.parse({
        cubeQuery: {},
        chartConfig: { type: 'rocket' },
        title: 'x',
      }),
    ).toThrow();
  });

  it('rejects missing title', () => {
    expect(() =>
      ChartResponseSchema.parse({
        cubeQuery: {},
        chartConfig: { type: 'bar' },
      }),
    ).toThrow();
  });
});

// resolveAiProvider reports which provider+model pair will be used. The
// ai_call_log.model column persists the returned `slug` for post-hoc cost
// attribution and eval grouping.
describe('resolveAiProvider — default provider + model', () => {
  const snap = { ...process.env };
  afterEach(() => {
    process.env = { ...snap };
  });

  it('defaults to openai + gpt-5-nano when AI_* env is unset', () => {
    delete process.env.AI_PROVIDER;
    delete process.env.AI_MODEL;
    const p = resolveAiProvider();
    expect(p.provider).toBe('openai');
    expect(p.model).toBe('gpt-5-nano');
    expect(p.slug).toBe('openai:gpt-5-nano');
  });

  it('honors AI_PROVIDER + AI_MODEL overrides', () => {
    process.env.AI_PROVIDER = 'claude';
    process.env.AI_MODEL = 'claude-sonnet-4-6';
    const p = resolveAiProvider();
    expect(p.provider).toBe('claude');
    expect(p.model).toBe('claude-sonnet-4-6');
    expect(p.slug).toBe('claude:claude-sonnet-4-6');
  });

  it('marks mock responses with a mock slug', () => {
    process.env.MOCK_AI = 'true';
    const p = resolveAiProvider();
    expect(p.provider).toBe('mock');
    expect(p.slug.startsWith('mock:')).toBe(true);
  });

  it('treats legacy MOCK_CLAUDE=true as mock for backwards compatibility', () => {
    delete process.env.MOCK_AI;
    process.env.MOCK_CLAUDE = 'true';
    const p = resolveAiProvider();
    expect(p.provider).toBe('mock');
  });
});

// The mock fixture remains a W1/W2-local-only shortcut so /api/ai/create-chart
// can be exercised end-to-end without any provider key. It is not the real
// contract.
describe('createChartFromPrompt mock fixture', () => {
  const snap = { ...process.env };
  afterEach(() => {
    process.env = { ...snap };
  });

  it('MOCK_CLAUDE=true still works (legacy)', async () => {
    process.env.MOCK_CLAUDE = 'true';
    delete process.env.MOCK_AI;
    const { response, usage } = await createChartFromPrompt('anything', '{}');
    expect(response.title).toContain('[MOCK]');
    expect(usage.input_tokens).toBe(0);
  });

  it('MOCK_AI=true works provider-agnostically', async () => {
    delete process.env.MOCK_CLAUDE;
    process.env.MOCK_AI = 'true';
    const { response } = await createChartFromPrompt('anything', '{}');
    expect(response.title).toContain('[MOCK]');
  });

  it('mock AdsCampaign query includes the required reportDate time filter', async () => {
    delete process.env.MOCK_CLAUDE;
    process.env.MOCK_AI = 'true';
    const { response } = await createChartFromPrompt('anything', '{}');

    expect(response.cubeQuery.timeDimensions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          dimension: 'AdsCampaign.reportDate',
          dateRange: expect.any(String),
        }),
      ]),
    );
  });
});

// OpenAI provider — the only hard contract we care about here is the wire
// shape the route will actually emit: Responses API, json_schema structured
// output, and usage tokens normalised into our existing shape.
describe('createChartFromPrompt — OpenAI provider (gpt-5-nano default)', () => {
  const snap = { ...process.env };
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).fetch = fetchMock;
  });

  afterEach(() => {
    process.env = { ...snap };
    vi.restoreAllMocks();
  });

  it('POSTs v1/responses with gpt-5-nano and a json_schema structured output', async () => {
    delete process.env.MOCK_CLAUDE;
    delete process.env.MOCK_AI;
    process.env.AI_PROVIDER = 'openai';
    process.env.AI_MODEL = 'gpt-5-nano';
    process.env.OPENAI_API_KEY = 'test-key';

    const structuredOutput = {
      cubeQuery: {
        measures: ['AdsCampaign.spend'],
        dimensions: ['Branch.branchName', 'AdsCampaign.sourceTier'],
      },
      chartConfig: { type: 'bar', x: 'Branch.branchName', y: 'AdsCampaign.spend' },
      title: '지점별 스펜드',
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        output_text: JSON.stringify(structuredOutput),
        usage: {
          input_tokens: 321,
          output_tokens: 89,
          input_tokens_details: { cached_tokens: 200 },
        },
      }),
    });

    const { response, usage } = await createChartFromPrompt('지점별 스펜드 막대 차트', '{"cubes":[]}');

    expect(response.title).toBe('지점별 스펜드');
    expect(usage.input_tokens).toBe(321);
    expect(usage.output_tokens).toBe(89);
    expect(usage.cache_read_input_tokens).toBe(200);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toBe('https://api.openai.com/v1/responses');
    const headers = init.headers as Record<string, string>;
    expect(headers.authorization).toBe('Bearer test-key');
    expect(headers['content-type']).toBe('application/json');

    const body = JSON.parse(init.body as string) as {
      model: string;
      input: unknown;
      text?: { format?: { type?: string; strict?: boolean } };
    };
    expect(body.model).toBe('gpt-5-nano');
    expect(Array.isArray(body.input)).toBe(true);
    expect(body.text?.format?.type).toBe('json_schema');
  });

  it('throws a clear error when OPENAI_API_KEY is missing', async () => {
    delete process.env.MOCK_CLAUDE;
    delete process.env.MOCK_AI;
    delete process.env.OPENAI_API_KEY;
    process.env.AI_PROVIDER = 'openai';

    await expect(createChartFromPrompt('x', '{}')).rejects.toThrow(/OPENAI_API_KEY/);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
