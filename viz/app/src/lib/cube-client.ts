export async function loadCubeData(
  cubeQuery: unknown,
  options?: { dashboardId?: string },
): Promise<{ data: Record<string, unknown>[]; usage?: unknown }> {
  const r = await fetch('/api/cube/load', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: cubeQuery, dashboardId: options?.dashboardId }),
  });
  if (!r.ok) throw new Error(`Cube load failed: ${r.status}`);
  return r.json();
}
