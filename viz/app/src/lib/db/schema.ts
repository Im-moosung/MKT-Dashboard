import { pgTable, uuid, varchar, text, jsonb, timestamp, integer, bigint } from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  googleSub: varchar('google_sub', { length: 255 }).notNull().unique(),
  displayName: varchar('display_name', { length: 255 }),
  avatarUrl: text('avatar_url'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  lastLoginAt: timestamp('last_login_at', { withTimezone: true }),
});

export const dashboards = pgTable('dashboards', {
  id: uuid('id').primaryKey().defaultRandom(),
  ownerId: uuid('owner_id').references(() => users.id, { onDelete: 'cascade' }).notNull(),
  title: varchar('title', { length: 255 }).notNull(),
  description: text('description'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
});

export const dashboardCharts = pgTable('dashboard_charts', {
  id: uuid('id').primaryKey().defaultRandom(),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }).notNull(),
  title: varchar('title', { length: 255 }).notNull(),
  gridX: integer('grid_x').notNull().default(0),
  gridY: integer('grid_y').notNull().default(0),
  gridW: integer('grid_w').notNull().default(6),
  gridH: integer('grid_h').notNull().default(4),
  cubeQueryJson: jsonb('cube_query_json').notNull(),
  chartConfigJson: jsonb('chart_config_json').notNull(),
  source: varchar('source', { length: 16 }).notNull().default('manual'),
  promptHistoryJson: jsonb('prompt_history_json'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
});

export const chatMessages = pgTable('chat_messages', {
  id: uuid('id').primaryKey().defaultRandom(),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }).notNull(),
  userId: uuid('user_id').references(() => users.id).notNull(),
  role: varchar('role', { length: 16 }).notNull(),
  content: text('content').notNull(),
  toolCallsJson: jsonb('tool_calls_json'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const shareTokens = pgTable('share_tokens', {
  id: uuid('id').primaryKey().defaultRandom(),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }).notNull(),
  token: varchar('token', { length: 64 }).notNull().unique(),
  createdBy: uuid('created_by').references(() => users.id).notNull(),
  expiresAt: timestamp('expires_at', { withTimezone: true }),
  revokedAt: timestamp('revoked_at', { withTimezone: true }),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const aiCallLog = pgTable('ai_call_log', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').references(() => users.id),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }),
  endpoint: varchar('endpoint', { length: 64 }).notNull(),
  model: varchar('model', { length: 64 }).notNull(),
  inputTokens: integer('input_tokens').default(0),
  outputTokens: integer('output_tokens').default(0),
  cacheReadTokens: integer('cache_read_tokens').default(0),
  costUsd: varchar('cost_usd', { length: 32 }),
  latencyMs: integer('latency_ms'),
  status: varchar('status', { length: 16 }).notNull(),
  error: text('error'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const bqQueryLog = pgTable('bq_query_log', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').references(() => users.id),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }),
  queryHash: varchar('query_hash', { length: 64 }).notNull(),
  estimatedBytes: bigint('estimated_bytes', { mode: 'number' }).notNull().default(0),
  actualBytes: bigint('actual_bytes', { mode: 'number' }),
  status: varchar('status', { length: 16 }).notNull(),
  error: text('error'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const usersRelations = relations(users, ({ many }) => ({ dashboards: many(dashboards) }));
export const dashboardsRelations = relations(dashboards, ({ one, many }) => ({
  owner: one(users, { fields: [dashboards.ownerId], references: [users.id] }),
  charts: many(dashboardCharts),
}));
