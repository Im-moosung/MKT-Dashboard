import { describe, it, expect } from 'vitest';
import * as schema from '@/lib/db/schema';

describe('db schema', () => {
  it('exposes users / dashboards / dashboardCharts / chatMessages / shareTokens / aiCallLog / bqQueryLog tables', () => {
    expect(schema.users).toBeDefined();
    expect(schema.dashboards).toBeDefined();
    expect(schema.dashboardCharts).toBeDefined();
    expect(schema.chatMessages).toBeDefined();
    expect(schema.shareTokens).toBeDefined();
    expect(schema.aiCallLog).toBeDefined();
    expect(schema.bqQueryLog).toBeDefined();
  });
});
