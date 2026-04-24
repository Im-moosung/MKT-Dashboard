# MKT-Viz W2 Truth Path Implementation Plan

> **For agentic workers:** W2 is not a UI expansion sprint. Keep work in small TDD PRs, preserve the W1 scope guard, and keep all `channels/`, `common/`, and `jobs/` paths out of scope unless the user explicitly approves otherwise.

**Goal:** Make the dashboard trustworthy on real data while keeping BigQuery usage inside the free tier. W2 must replace the mock-only AI path with a provider-agnostic LLM path using `gpt-5-nano` as the default model.

**Current baseline:** W1 local infrastructure MVP works with mock auth and mock AI. AI mock chart persist/reload, manual builder persist/reload, grid drag/resize persistence, and chat history reload have passed browser smoke. Share smoke is deferred by user priority. BigQuery currently contains real advertising data loaded by the previous project version through advertising APIs only. AMNY/DSTX sheet advertising data is missing from the current ad mart, and Sales/Orders plus Surveys real-data ingestion is not implemented yet. AdsCampaign query execution is also blocked by BigQuery mart view partition-filter behavior.

---

## Product Decisions

- **LLM default:** `gpt-5-nano`.
- **LLM challenger:** `gemini-2.5-flash-lite`.
- **LLM fallback/baseline:** `claude-sonnet-4-6`, not for normal daily use because of cost.
- **Implementation direction:** replace direct `claude-client.ts` coupling with a small provider abstraction. Use a common `ChartResponse` contract and provider-specific structured-output adapters.
- **Build / Explore language:** internal only. User-facing UI should expose a simple `편집` affordance, not `Build Mode`, `Explore Mode`, route splits, query params, or DB mode columns.
- **BigQuery cost rule:** user-facing dashboard queries must stay within the BigQuery free tier. W2 must add an app-level monthly usage meter and query guardrails.

---

## External Inputs

- [ ] OpenAI API key for `gpt-5-nano`
- [ ] Optional Gemini API key for `gemini-2.5-flash-lite` challenger eval
- [ ] Optional Anthropic API key only if keeping Claude fallback live
- [ ] Google OAuth client ID/secret for `@dstrict.com`
- [ ] BigQuery service account JSON
- [ ] BQ mart view partition-filter fix owner: user / DBA / deferred
- [ ] Confirm source tables/views for existing API-loaded advertising data
- [ ] AMNY/DSTX sheet data inclusion path for AdsCampaign
- [ ] Sales/Orders real data source, grain, freshness, and owner
- [ ] Surveys real data source, grain, freshness, and owner
- [ ] Eval prompt corpus: minimum 10 marketing questions

---

## W2 Tasks

### Task 0: Data Source Audit + Contract Freeze

**Goal:** Make every cube honest about whether it is real, partial, sheet-backed, demo, or unknown before using it in AI-generated dashboards.

- [x] Audit AdsCampaign, Orders, Surveys, Branch, and Channel current BigQuery sources.
- [x] Record source table/view, grain, branch coverage, freshness expectation, owner, and source tier.
- [x] Use source tiers: `real`, `partial_real`, `sheet`, `demo`, `unknown`.
- [x] Treat AdsCampaign as `partial_real` until API ad data and AMNY/DSTX sheet ad data are unified or coverage limitations are visible in the UI.
- [x] Treat Sales/Orders and Surveys as `demo` or `unknown` until real ingestion is implemented and verified.
- [ ] Define how source tier is exposed through Cube metadata and chart persistence.
  - 2026-04-24: Cube metadata has `AdsCampaign.sourceTier`; chart persistence-level tier snapshot is still pending.

**Done when:** W2 workers can tell which cubes are safe for real product claims, which are partial, and which must be hidden or labeled as demo/unknown.

### Task 1: W1 Closure + W2 Scope Freeze

**Goal:** Close W1 as local infrastructure MVP and make W2 scope unambiguous.

- [x] Update `docs/status.md` to point to this W2 plan.
- [x] Mark share smoke as deferred, not a W2 blocker.
- [x] Record GPT nano default model decision.
- [x] Record BigQuery free-tier guardrail decision.
- [x] Record AdsCampaign as API-real but AMNY/DSTX-incomplete.
- [x] Record Sales/Orders and Surveys as not product-real until ingestion is implemented.

**Done when:** New workers can start from `docs/status.md` and this plan without re-litigating W1/W2 boundaries.

### Task 2: BigQuery Free Tier Guardrail

**Goal:** User-facing dashboard queries remain inside the free tier and show approximate monthly usage.

- [x] Add `bq_query_log` app DB table or equivalent app-level log.
- [x] Log `userId`, `dashboardId`, query hash, estimated bytes, actual bytes when available, status, and timestamp.
- [x] Add monthly usage calculation against 1 TiB free-tier query budget.
- [x] Show owner/admin badge: `이번 달 BigQuery 사용량 (앱 기준) · N%`.
- [x] Add tooltip: app-executed query usage only; direct BigQuery console usage is not included.
- [x] Enforce thresholds: 70% warning, 85% caution, 95% block.
- [x] Add tests for month boundary and 95% blocking.

**Date policy:** Do not use a hard 90-day maximum. Use bytes-first gating. Default to recent 30 days for day-level marts, then allow longer ranges when estimated bytes are safe. Monthly summary/pre-aggregated marts can allow wider ranges.

**Done when:** App-mediated queries cannot continue after the 95% threshold, and the UI shows a clear app-level usage percentage.

### Task 3: AdsCampaign Coverage + Real-Data Unblock

**Goal:** AdsCampaign becomes queryable under the cost guardrail without hiding incomplete branch coverage.

- [x] Prefer BQ mart view/materialized layer fix so partition filters push down correctly.
- [ ] If BQ DDL is delayed, implement a Cube-level workaround only as a fallback.
- [x] Ensure AdsCampaign queries use mart/pre-aggregated data, not raw/core fact scans.
- [x] Verify which API-loaded ad branches/channels are currently present in BigQuery.
- [x] Add or wire AMNY/DSTX sheet ad data into the AdsCampaign mart, or explicitly mark AdsCampaign as `partial_real` with missing AMNY/DSTX coverage.
- [ ] Add or update smoke: Cube `/load` for AdsCampaign real measures returns data and stays under byte guard.
  - 2026-04-24: direct Cube `/load` returns AMNY/DSTX data; authenticated app-route guardrail smoke still pending.

**Done when:** AdsCampaign `/load` succeeds, the usage meter/guardrail records the query, and the UI/metadata honestly indicates whether AMNY/DSTX are included.

### Task 4: LLM Provider Abstraction + GPT Nano Default

**Goal:** Remove hard dependency on Anthropic for chart generation.

- [x] Add a common LLM chart-generation interface around `ChartResponse`.
- [x] Implement OpenAI provider with `gpt-5-nano` as default.
- [x] Keep existing Claude implementation as fallback/baseline if key is available.
- [ ] Add optional Gemini Flash-Lite challenger provider behind config.
- [x] Replace `CLAUDE_API_KEY`-centric config language with provider-neutral `AI_PROVIDER`, `AI_MODEL`, and provider keys.
- [x] Preserve `MOCK_CLAUDE=true` or rename to a provider-neutral mock flag in a small follow-up if needed.

**Done when:** `AI_PROVIDER=openai` and `AI_MODEL=gpt-5-nano` can generate a schema-valid `ChartResponse` in tests.

### Task 5: Eval Scaffold + Model Selection

**Goal:** Choose models by evidence, not preference.

- [ ] Create at least 10 marketing eval prompts.
- [ ] Run `gpt-5-nano`, `gemini-2.5-flash-lite`, and `claude-sonnet-4-6` baseline when keys exist.
- [ ] Track schema-valid ratio, Cube `/load` success, intent match, p50/p95 latency, request cost, and Korean title quality.

**Promotion bar:** schema-valid >= 0.90, `/load` success >= 0.85, intent match >= 0.80, p95 latency <= 3s. `gpt-5-nano` remains primary unless the challenger beats it on quality and cost.

### Task 6: Google SSO Real Path

**Goal:** Replace mock login with real Google SSO.

- [ ] Add/verify OAuth client config for localhost callback.
- [x] Handle mock email -> real Google sub migration or conflict-safe upsert by email.
- [ ] Verify `@dstrict.com` allowed and external domains rejected.
- [ ] Run browser E2E with `MOCK_AUTH=false`.

### Task 7: Route/API Quality Required For W2

**Goal:** Fix only route/API issues that affect the truth path.

- [x] Ensure AI-created charts persist server-side exactly once.
- [ ] Add route-level integration coverage for create-chart success/failure paths.
- [x] Verify `ai_call_log` records provider/model/token/cost-relevant fields.
- [ ] Keep unrelated backlog items out unless they block W2 smoke.

### Task 8: Lightweight Edit Chrome

**Goal:** Add minimal edit affordance without strong Build / Explore mode.

- [ ] Keep `/d/[id]` as the single dashboard route.
- [ ] Do not add `?mode=build`, `/edit`, Draft/Published DB columns, or dashboard mode columns.
- [ ] Owner can reveal editing chrome: AI panel, chart add, drag handles, chart settings.
- [ ] Share-token viewers must not see edit affordances.
- [ ] Exploration interactions must continue when edit chrome is hidden.

### Task 9: Sales/Orders + Surveys Real-Data Backlog

**Goal:** Prevent seed/test data from being mistaken for product-real data while preparing the next real-data domains.

- [ ] Keep Orders and Surveys visible only with `demo`/`unknown` labeling until their real sources are implemented.
- [ ] Document required source systems, grain, refresh cadence, branch coverage, and ownership.
- [ ] Do not let AI eval prompts assume Orders/Surveys are real unless source tier is upgraded.

**Done when:** W2 can proceed on the ad truth path, and Sales/Surveys have a concrete ingestion contract for the next data sprint.

---

## W2 Exit Criteria

- [ ] AdsCampaign real-data `/load` succeeds under BigQuery guardrail.
- [ ] AdsCampaign source tier is explicit; if AMNY/DSTX are not included, the product shows `partial_real`/coverage limitation.
- [ ] Orders and Surveys are not silently presented as real until their ingestion is implemented.
- [ ] Monthly BigQuery usage badge displays app-level percent of 1 TiB.
- [ ] 70/85/95% BigQuery thresholds have tests and browser smoke.
- [ ] `gpt-5-nano` is the default AI chart model.
- [ ] Eval scaffold runs at least 10 prompts and records model metrics.
- [ ] Real Google SSO works with mock-user conflict handled.
- [ ] Real AI chart create -> Cube load -> persist -> reload works.
- [ ] Lightweight edit chrome follows the no-strong-mode guardrails.
- [ ] `pnpm lint`, relevant vitest tests, and relevant Python tests pass.
- [ ] `docs/status.md` has W2 closure notes and W3 next action.
