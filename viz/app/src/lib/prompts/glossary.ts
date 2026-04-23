export const GLOSSARY_KO = `
아르떼뮤지엄 지점 코드:
- AMLV=Las Vegas, AMNY=New York, AMBS=부산, AMDB=Dubai, AMGN=강릉, AMJJ=제주, AMYS=여수, AKJJ=키즈파크
- DSTX=reSOUND New York

채널 코드 예:
- META, GOOGLE_ADS, TIKTOK_ADS, NAVER_ADS (API 직접 수집)
- YOUTUBE, AFFILIATE, EMAIL, INFLUENCER, COUPON, OTA, ORGANIC_SEO, GOOGLE_DEMAND_GEN (대행사 시트)

메트릭 정의:
- 스펜드(spend) = 광고 비용, native currency
- ROAS = conversion_value / spend
- CPC = spend / clicks
- CTR = clicks / impressions (%)
- NPS = avg_answer_score

주요 뷰/큐브:
- AdsCampaign: 광고 캠페인 일별 집계
- Orders: 주문/매출 일별
- Surveys: 설문 일별 평균
- Branch, Channel (dim)

기본 기간: 미지정 시 최근 30일.
`;
