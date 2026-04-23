# W1 Smoke Test Scenarios

MKT-Viz W1 로컬 MVP 수동 브라우저 검증 체크리스트.

**환경**: `MOCK_AUTH=true` + `MOCK_CLAUDE=true`
**전제**: `docker compose up -d` (cube/postgres/redis Up) + `pnpm dev` 실행 중

---

## Scenario 1: AI 차트 생성 → 저장 → 새로고침 복원

**목표**: 로그인 후 대시보드 생성, AI 패널로 차트 추가, 저장, 새로고침 시 복원.

### 실행 단계

1. `http://localhost:3000` 접속
2. Mock 이메일(`dev@dstrict.com`) 입력 후 "Mock 로그인" 클릭
3. 대시보드 목록 페이지 표시 확인
4. "새 대시보드" 버튼 클릭 → 제목 입력 ("테스트 대시보드") → 생성
5. 대시보드 상세 `/d/[id]` 진입 확인
6. 우측 AI 사이드 패널 열기
7. 입력창에 "최근 7일 Meta 스펜드 추이" 입력 후 전송
8. `[MOCK] Line chart` 응답 수신 확인 (MOCK_CLAUDE=true)
9. "차트 저장" 버튼 클릭
10. 그리드에 차트 타일 표시 확인
11. 브라우저 새로고침 (`Cmd+R`)
12. 차트 타일 그대로 복원 확인

### 기대 결과

- 로그인 성공: 대시보드 목록 표시
- AI 응답: `[MOCK]` 접두어를 가진 Line chart 스텁
- 새로고침 후: 동일 차트 유지 (DB persist)

### 검증

- [ ] PASS — 모든 단계 정상
- [ ] FAIL — 실패 단계: ____________

---

## Scenario 2: 수동 빌더 차트 + AI 차트 혼합 그리드

**목표**: 수동 빌더로 차트 생성 후 AI 차트 추가, 2개 타일이 그리드에 공존.

### 실행 단계

1. 로그인 → 기존 또는 새 대시보드 진입
2. "+ 차트 추가" 또는 "수동 빌드" 버튼 클릭
3. QueryBuilder에서:
   - Measure: `Orders.totalRevenue` 선택
   - Dimension: `Channel.channelName` 선택
   - "미리보기" 클릭 → Bar chart 미리보기 확인
4. "저장" 클릭 → 그리드에 Bar chart 타일 1개 확인
5. AI 패널에서 "최근 30일 채널별 CPC" 입력 후 전송
6. `[MOCK] Line chart` 응답 → "차트 저장"
7. 그리드에 타일 2개 (Bar + Line) 표시 확인
8. 새로고침 → 2개 모두 복원 확인

### 기대 결과

- 수동 차트: Cube 메타 기반 Bar chart
- AI 차트: [MOCK] Line chart stub
- 그리드: 2개 타일 동시 표시 + DB persist

### 검증

- [ ] PASS — 모든 단계 정상
- [ ] FAIL — 실패 단계: ____________

---

## Scenario 3: 그리드 Drag/Resize → 새로고침 → 레이아웃 유지

**목표**: 차트 타일 위치·크기 변경 후 새로고침해도 레이아웃 유지.

### 전제

Scenario 1 또는 2 완료 후 그리드에 1개 이상 타일 존재.

### 실행 단계

1. 대시보드 `/d/[id]` 진입
2. 차트 타일을 드래그해 다른 위치로 이동
3. 타일 우하단 핸들을 드래그해 크기 조정
4. 잠시 대기 (debounce ~500ms 후 PATCH 자동 저장)
5. 브라우저 새로고침 (`Cmd+R`)
6. 이동·리사이즈한 위치/크기 그대로 복원 확인

### 기대 결과

- PATCH `/api/charts/[id]` 호출 확인 (DevTools Network 탭)
- `layout` JSON (x/y/w/h) DB 저장
- 새로고침 후 동일 레이아웃 렌더

### curl 보조 검증

```bash
# 저장 후 차트 레이아웃 확인 (id는 브라우저 URL 또는 GET /api/dashboards 응답에서 획득)
curl -s http://localhost:3000/api/dashboards \
  -H "Cookie: $(cat /tmp/mkt-viz-cookie.txt)" | python3 -m json.tool | head -40
```

### 검증

- [ ] PASS — 새로고침 후 위치/크기 동일
- [ ] FAIL — 실패 단계: ____________

---

## Scenario 4: 공유 링크 생성 → read-only 접근

**목표**: 공유 링크 생성 후 다른 @dstrict.com 계정(시크릿 창)에서 read-only 확인.

### 실행 단계

1. 대시보드 `/d/[id]` 진입 (로그인 상태)
2. 우상단 "공유" 버튼 클릭
3. ShareDialog에서 "공유 링크 생성" 클릭
4. 생성된 URL 복사 (형식: `http://localhost:3000/shared/[token]`)
5. 시크릿 창(또는 다른 브라우저)에서 공유 URL 접속
6. 별도 Mock 이메일(`other@dstrict.com`)로 로그인 (시크릿 창)
7. 대시보드 read-only 뷰 표시 확인
8. 편집 버튼 없음 + 차트 타일 동일하게 표시 확인

### 기대 결과

- 공유 URL: `GET /shared/[token]` → 200
- 다른 계정: 차트 읽기 가능, 수정 UI 없음
- 만료 없음 (POC 기간): 공유 토큰 영구 유효

### curl 보조 검증

```bash
# 공유 토큰 직접 확인 (token은 ShareDialog에서 복사)
curl -s "http://localhost:3000/shared/<TOKEN>" -o /dev/null -w "%{http_code}\n"
# 200 기대 (로그인 필요 여부는 미들웨어 설정에 따름)
```

### 검증

- [ ] PASS — read-only 뷰 정상, 편집 불가
- [ ] FAIL — 실패 단계: ____________

---

## Scenario 5: 한글/영어 혼합 AI 질의 5건

**목표**: 한글 3건 + 영어 2건 AI 질의, 모두 응답 수신.

> **주의**: `MOCK_CLAUDE=true` 환경에서는 질의 내용과 무관하게 항상 `[MOCK] Line chart` 고정 응답을 반환. 실제 언어별 정확도 검증은 Anthropic API 키 발급 후 `MOCK_CLAUDE=false` 전환 시 가능.

### 실행 단계

대시보드 `/d/[id]`의 AI 사이드 패널에서 아래 5개 질의를 순서대로 입력:

| # | 질의 | 언어 | MOCK 기대 응답 |
|---|------|------|----------------|
| 1 | "최근 7일 Meta 스펜드 추이" | 한국어 | `[MOCK] Line chart` |
| 2 | "채널별 전환율 비교" | 한국어 | `[MOCK] Line chart` |
| 3 | "지난달 캠페인별 ROAS 상위 5개" | 한국어 | `[MOCK] Line chart` |
| 4 | "Show me last 7 days spend by channel" | 영어 | `[MOCK] Line chart` |
| 5 | "Top 10 campaigns by revenue this month" | 영어 | `[MOCK] Line chart` |

각 질의 후:
1. AI 응답 메시지 수신 확인
2. "차트 저장" 클릭 (선택)
3. 다음 질의 입력

### 기대 결과 (MOCK_CLAUDE=true)

- 5/5 응답 수신 (에러 없음)
- 모든 응답에 `[MOCK]` 접두어 포함
- 채팅 히스토리가 패널에 누적 표시

### 실제 검증 (MOCK_CLAUDE=false, Anthropic 키 발급 후)

- 5/5 의미 있는 Cube query 생성 + 차트 렌더
- 한글 질의 → 한국어 컬럼명 인식 + 올바른 measure/dimension 선택
- 영어 질의 → 동일 정확도

### 검증

- [ ] PASS — 5/5 응답 수신, 에러 없음
- [ ] FAIL — 실패 건: ____________

---

## 전체 결과 요약

| Scenario | 결과 | 비고 |
|----------|------|------|
| S1: AI 차트 생성 → 복원 | [ ] PASS / [ ] FAIL | |
| S2: 수동 + AI 혼합 그리드 | [ ] PASS / [ ] FAIL | |
| S3: Drag/Resize 레이아웃 유지 | [ ] PASS / [ ] FAIL | |
| S4: 공유 링크 read-only | [ ] PASS / [ ] FAIL | |
| S5: 한글+영어 5건 AI 질의 | [ ] PASS / [ ] FAIL | |

**W1 종료 조건**: 5/5 PASS 시 W2 진입 가능.

> 브라우저 smoke 검증은 사용자 수동 실행. 자동화 E2E (Playwright) 는 W2 Task에서 구현 예정.
