export async function loadCubeData(cubeQuery: unknown): Promise<{ data: Record<string, unknown>[] }> {
  const r = await fetch('/api/cube/load', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: cubeQuery }),
  });
  if (!r.ok) throw new Error(`Cube load failed: ${r.status}`);
  return r.json();
}
