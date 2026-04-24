import { db } from './client';
import { users, dashboards, dashboardCharts } from './schema';
import { eq, and, desc } from 'drizzle-orm';

export async function upsertUserByGoogle(payload: {
  email: string;
  googleSub: string;
  displayName?: string;
  avatarUrl?: string;
}) {
  const bySub = await db
    .select()
    .from(users)
    .where(eq(users.googleSub, payload.googleSub))
    .limit(1);
  if (bySub.length) {
    const [updated] = await db
      .update(users)
      .set({
        lastLoginAt: new Date(),
        displayName: payload.displayName,
        avatarUrl: payload.avatarUrl,
      })
      .where(eq(users.id, bySub[0].id))
      .returning();
    return updated ?? bySub[0];
  }

  // Same email may already exist under a different googleSub (e.g., a mock-auth
  // seed row being promoted to a real Google sub). email is UNIQUE, so plain
  // INSERT would throw — reconcile by updating the existing row's googleSub.
  const byEmail = await db
    .select()
    .from(users)
    .where(eq(users.email, payload.email))
    .limit(1);
  if (byEmail.length) {
    const [updated] = await db
      .update(users)
      .set({
        googleSub: payload.googleSub,
        displayName: payload.displayName,
        avatarUrl: payload.avatarUrl,
        lastLoginAt: new Date(),
      })
      .where(eq(users.id, byEmail[0].id))
      .returning();
    return updated ?? byEmail[0];
  }

  const [u] = await db.insert(users).values(payload).returning();
  return u;
}

export async function createUser(payload: {
  email: string;
  googleSub: string;
  displayName?: string;
}) {
  const [u] = await db.insert(users).values(payload).returning();
  return u;
}

export async function listDashboards(ownerId: string) {
  return db
    .select()
    .from(dashboards)
    .where(eq(dashboards.ownerId, ownerId))
    .orderBy(desc(dashboards.updatedAt));
}

export async function createDashboard(payload: {
  ownerId: string;
  title: string;
  description?: string;
}) {
  const [d] = await db.insert(dashboards).values(payload).returning();
  return d;
}

export async function getDashboard(id: string, ownerId: string) {
  const rows = await db
    .select()
    .from(dashboards)
    .where(and(eq(dashboards.id, id), eq(dashboards.ownerId, ownerId)))
    .limit(1);
  return rows[0] ?? null;
}

export async function updateDashboard(
  id: string,
  ownerId: string,
  patch: { title?: string; description?: string },
) {
  const [d] = await db
    .update(dashboards)
    .set({ ...patch, updatedAt: new Date() })
    .where(and(eq(dashboards.id, id), eq(dashboards.ownerId, ownerId)))
    .returning();
  return d ?? null;
}

export async function deleteDashboard(id: string, ownerId: string) {
  await db
    .delete(dashboards)
    .where(and(eq(dashboards.id, id), eq(dashboards.ownerId, ownerId)));
}

export async function listChartsByDashboard(dashboardId: string) {
  return db
    .select()
    .from(dashboardCharts)
    .where(eq(dashboardCharts.dashboardId, dashboardId));
}

export async function createChart(payload: {
  dashboardId: string;
  title: string;
  cubeQueryJson: unknown;
  chartConfigJson: unknown;
  source: 'ai' | 'manual' | 'hybrid';
  promptHistoryJson?: unknown;
  gridX?: number;
  gridY?: number;
  gridW?: number;
  gridH?: number;
}) {
  const [c] = await db
    .insert(dashboardCharts)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .values(payload as any)
    .returning();
  return c;
}

export async function updateChart(
  id: string,
  dashboardId: string,
  patch: Partial<{
    title: string;
    cubeQueryJson: unknown;
    chartConfigJson: unknown;
    gridX: number;
    gridY: number;
    gridW: number;
    gridH: number;
  }>,
) {
  const [c] = await db
    .update(dashboardCharts)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .set({ ...patch, updatedAt: new Date() } as any)
    .where(and(eq(dashboardCharts.id, id), eq(dashboardCharts.dashboardId, dashboardId)))
    .returning();
  return c ?? null;
}

export async function deleteChart(id: string, dashboardId: string) {
  await db
    .delete(dashboardCharts)
    .where(and(eq(dashboardCharts.id, id), eq(dashboardCharts.dashboardId, dashboardId)));
}
