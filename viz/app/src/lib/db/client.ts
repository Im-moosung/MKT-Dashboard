import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

const globalForDb = globalThis as unknown as { _pgClient?: postgres.Sql };
const queryClient = globalForDb._pgClient ?? postgres(process.env.DATABASE_URL!);
if (process.env.NODE_ENV !== 'production') {
  globalForDb._pgClient = queryClient;
}
export const db = drizzle(queryClient, { schema });
