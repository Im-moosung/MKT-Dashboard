import Anthropic from '@anthropic-ai/sdk';
import { z } from 'zod';
import { GLOSSARY_KO } from './prompts/glossary';
import { CHART_CREATE_INSTRUCTIONS } from './prompts/chart-create';

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

const CREATE_CHART_TOOL = {
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
};

const MOCK_RESPONSE: ChartResponse = ChartResponseSchema.parse({
  cubeQuery: {
    measures: ['AdsCampaign.spend'],
    timeDimensions: [
      { dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 7 days' },
    ],
  },
  chartConfig: {
    type: 'line',
    x: 'AdsCampaign.reportDate',
    y: 'AdsCampaign.spend',
    title: '[MOCK] 최근 7일 스펜드',
  },
  title: '[MOCK] 최근 7일 스펜드',
});

export async function createChartFromPrompt(
  prompt: string,
  cubeMetaJson: string,
): Promise<{
  response: ChartResponse;
  usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number };
}> {
  if (process.env.MOCK_CLAUDE === 'true') {
    return {
      response: MOCK_RESPONSE,
      usage: { input_tokens: 0, output_tokens: 0 },
    };
  }

  const anthropic = new Anthropic({ apiKey: process.env.CLAUDE_API_KEY! });

  const r = await anthropic.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2048,
    system: [
      { type: 'text', text: GLOSSARY_KO, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: `Cube meta:\n${cubeMetaJson}`, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: CHART_CREATE_INSTRUCTIONS, cache_control: { type: 'ephemeral' } },
    ] as Parameters<typeof anthropic.messages.create>[0]['system'],
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    tools: [CREATE_CHART_TOOL] as any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    tool_choice: { type: 'tool', name: 'create_chart' } as any,
    messages: [{ role: 'user', content: prompt }],
  });

  const block = r.content.find((b) => b.type === 'tool_use') as
    | { type: 'tool_use'; input: unknown }
    | undefined;
  if (!block) throw new Error('No tool_use in response');

  const parsed = ChartResponseSchema.parse(block.input);
  return { response: parsed, usage: r.usage as { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number } };
}
