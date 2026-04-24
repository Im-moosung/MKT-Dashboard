import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import {
  createUser,
  createDashboard,
  listDashboards,
  getDashboard,
  updateDashboard,
  deleteDashboard,
  createChart,
  updateChart,
  deleteChart,
  listChartsByDashboard,
  upsertUserByGoogle,
} from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

describe('db queries', () => {
  let userId: string;
  let dashboardId: string;

  beforeAll(async () => {
    const u = await createUser({
      email: 'test-queries@dstrict.com',
      googleSub: 'sub-test-queries-001',
      displayName: 'Query Tester',
    });
    userId = u.id;
  });

  afterAll(async () => {
    await db.delete(users).where(eq(users.id, userId));
  });

  it('creates a user and returns uuid', () => {
    expect(userId).toBeTruthy();
    expect(typeof userId).toBe('string');
  });

  it('creates and lists dashboards owned by user', async () => {
    const d = await createDashboard({ ownerId: userId, title: '테스트 대시보드' });
    dashboardId = d.id;
    expect(d.title).toBe('테스트 대시보드');
    expect(d.ownerId).toBe(userId);

    const list = await listDashboards(userId);
    expect(list.some((x) => x.id === d.id)).toBe(true);
  });

  it('getDashboard returns dashboard for correct owner', async () => {
    const d = await getDashboard(dashboardId, userId);
    expect(d).not.toBeNull();
    expect(d!.id).toBe(dashboardId);
  });

  it('getDashboard returns null for wrong owner', async () => {
    const d = await getDashboard(dashboardId, '00000000-0000-0000-0000-000000000000');
    expect(d).toBeNull();
  });

  it('updateDashboard patches title and returns updated row', async () => {
    const updated = await updateDashboard(dashboardId, userId, { title: '수정된 대시보드' });
    expect(updated).not.toBeNull();
    expect(updated!.title).toBe('수정된 대시보드');
  });

  it('updateDashboard returns null for wrong owner', async () => {
    const updated = await updateDashboard(dashboardId, '00000000-0000-0000-0000-000000000000', { title: 'FAIL' });
    expect(updated).toBeNull();
  });

  describe('chart CRUD', () => {
    let chartId: string;

    it('createChart inserts and returns chart', async () => {
      const c = await createChart({
        dashboardId,
        title: '테스트 차트',
        cubeQueryJson: { measures: ['Orders.orders'] },
        chartConfigJson: { type: 'bar' },
        source: 'manual',
      });
      chartId = c.id;
      expect(c.title).toBe('테스트 차트');
      expect(c.dashboardId).toBe(dashboardId);
    });

    it('listChartsByDashboard returns chart', async () => {
      const charts = await listChartsByDashboard(dashboardId);
      expect(charts.some((c) => c.id === chartId)).toBe(true);
    });

    it('updateChart patches title using (id, dashboardId, patch) signature', async () => {
      const updated = await updateChart(chartId, dashboardId, { title: '수정된 차트' });
      expect(updated).not.toBeNull();
      expect(updated!.title).toBe('수정된 차트');
    });

    it('updateChart returns null for wrong dashboardId', async () => {
      const updated = await updateChart(chartId, '00000000-0000-0000-0000-000000000000', { title: 'FAIL' });
      expect(updated).toBeNull();
    });

    it('deleteChart removes chart using (id, dashboardId) signature', async () => {
      await deleteChart(chartId, dashboardId);
      const charts = await listChartsByDashboard(dashboardId);
      expect(charts.some((c) => c.id === chartId)).toBe(false);
    });
  });

  it('deleteDashboard removes dashboard', async () => {
    await deleteDashboard(dashboardId, userId);
    const d = await getDashboard(dashboardId, userId);
    expect(d).toBeNull();
  });
});

describe('upsertUserByGoogle — mock→real Google sub reconciliation', () => {
  const email = 'upsert-conflict@dstrict.com';
  const mockSub = `mock:${email}`;
  const realSub = 'google-oauth2-real-sub-abcdef';

  afterAll(async () => {
    await db.delete(users).where(eq(users.email, email));
  });

  it('re-upserting with a different googleSub for the same email updates the existing row instead of throwing', async () => {
    // Seed — mock login path creates the row.
    const mockRow = await upsertUserByGoogle({
      email,
      googleSub: mockSub,
      displayName: 'Mock User',
    });
    expect(mockRow.email).toBe(email);
    expect(mockRow.googleSub).toBe(mockSub);

    // Real Google OAuth arrives for the same email with a different sub.
    const realRow = await upsertUserByGoogle({
      email,
      googleSub: realSub,
      displayName: 'Real Google User',
      avatarUrl: 'https://example.com/a.png',
    });

    // Same identity — same id — but promoted to the real googleSub.
    expect(realRow.id).toBe(mockRow.id);
    expect(realRow.googleSub).toBe(realSub);
    expect(realRow.displayName).toBe('Real Google User');
    expect(realRow.avatarUrl).toBe('https://example.com/a.png');

    const rows = await db.select().from(users).where(eq(users.email, email));
    expect(rows.length).toBe(1);
    expect(rows[0].googleSub).toBe(realSub);
    expect(rows[0].displayName).toBe('Real Google User');
    expect(rows[0].avatarUrl).toBe('https://example.com/a.png');
  });
});
