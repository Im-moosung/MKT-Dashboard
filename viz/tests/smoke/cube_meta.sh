#!/usr/bin/env bash
# W1 smoke: Cube /meta exposes 5 cubes and /load succeeds for Branch + Orders.
# AdsCampaign /load is intentionally skipped — mart.v_dashboard_campaign_daily
# does not propagate the required partition filter to the underlying
# core.fact_marketing_action_daily table. Fix the mart view in BigQuery
# (outside viz scope); see docs/status.md.
set -euo pipefail
BASE="${CUBE_BASE_URL:-http://localhost:4000/cubejs-api/v1}"
TOKEN=$(docker exec viz-cube-1 node -e "console.log(require('jsonwebtoken').sign({user_id:'smoke',email:'smoke@dstrict.com'},process.env.CUBEJS_API_SECRET,{algorithm:'HS256',expiresIn:'5m'}))")

echo "--- /meta ---"
META=$(curl -fsS "$BASE/meta" -H "authorization: $TOKEN")
NAMES=$(printf '%s' "$META" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(",".join(sorted(c.get("name") for c in d.get("cubes",[]))))')
EXPECTED="AdsCampaign,Branch,Channel,Orders,Surveys"
echo "cubes=$NAMES"
if [ "$NAMES" != "$EXPECTED" ]; then
  echo "FAIL: expected $EXPECTED got $NAMES"
  exit 1
fi

echo "--- /load Branch ---"
curl -fsS -X POST "$BASE/load" -H "authorization: $TOKEN" -H "content-type: application/json" \
  -d '{"query":{"dimensions":["Branch.branchId","Branch.branchName"]}}' \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);rows=len(d.get("data",[]));print(f"rows={rows}");sys.exit(0 if rows>0 else 1)'

echo "--- /load Orders (schema-level query; 0 rows OK) ---"
curl -fsS -X POST "$BASE/load" -H "authorization: $TOKEN" -H "content-type: application/json" \
  -d '{"query":{"measures":["Orders.orders"],"timeDimensions":[{"dimension":"Orders.reportDate","granularity":"day","dateRange":"last 7 days"}]}}' \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);err=d.get("error");print("error:",err);sys.exit(1 if err else 0)'

echo "PASS"
