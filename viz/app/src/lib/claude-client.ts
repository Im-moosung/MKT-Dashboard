// Back-compat shim — `claude-client` was the W1 file name before the provider
// abstraction landed. Everything now lives in `@/lib/ai/provider`. Existing
// callers (route handlers, tests) keep importing from here.
export {
  ChartResponseSchema,
  createChartFromPrompt,
  resolveAiProvider,
  type ChartResponse,
  type ResolvedProvider,
  type Usage,
} from './ai/provider';
