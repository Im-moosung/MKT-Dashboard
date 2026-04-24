type ContractOk = { ok: true };
type ContractError = {
  ok: false;
  code:
    | 'ads_campaign_report_date_required'
    | 'orders_report_date_required'
    | 'surveys_report_date_required';
  message: string;
};

export type CubeQueryContractResult = ContractOk | ContractError;

const REQUIRED_TIME_DIMENSIONS = [
  {
    cube: 'AdsCampaign',
    timeDimension: 'AdsCampaign.reportDate',
    code: 'ads_campaign_report_date_required',
  },
  {
    cube: 'Orders',
    timeDimension: 'Orders.reportDate',
    code: 'orders_report_date_required',
  },
  {
    cube: 'Surveys',
    timeDimension: 'Surveys.reportDate',
    code: 'surveys_report_date_required',
  },
] as const;

export function validateCubeQueryContract(query: unknown): CubeQueryContractResult {
  for (const contract of REQUIRED_TIME_DIMENSIONS) {
    if (!touchesCube(query, contract.cube)) continue;
    if (hasTimeDimensionDateRange(query, contract.timeDimension)) continue;

    return {
      ok: false,
      code: contract.code,
      message: `${contract.cube} queries require ${contract.timeDimension} dateRange for BigQuery partition pruning.`,
    };
  }

  return { ok: true };
}

function hasTimeDimensionDateRange(query: unknown, timeDimension: string): boolean {
  return getArrayField(query, 'timeDimensions').some((td) => {
    if (!td || typeof td !== 'object') return false;
    const rec = td as Record<string, unknown>;
    return rec.dimension === timeDimension && hasDateRange(rec.dateRange);
  });
}

function touchesCube(query: unknown, cube: string): boolean {
  const members = [
    ...getStringArrayField(query, 'measures'),
    ...getStringArrayField(query, 'dimensions'),
    ...getStringArrayField(query, 'segments'),
    ...getArrayField(query, 'timeDimensions')
      .map((td) => (td && typeof td === 'object' ? (td as Record<string, unknown>).dimension : undefined))
      .filter((value): value is string => typeof value === 'string'),
    ...extractFilterMembers(getArrayField(query, 'filters')),
  ];

  return members.some((member) => member.startsWith(`${cube}.`));
}

function getArrayField(query: unknown, field: string): unknown[] {
  if (!query || typeof query !== 'object') return [];
  const value = (query as Record<string, unknown>)[field];
  return Array.isArray(value) ? value : [];
}

function getStringArrayField(query: unknown, field: string): string[] {
  return getArrayField(query, field).filter((value): value is string => typeof value === 'string');
}

function extractFilterMembers(filters: unknown[]): string[] {
  return filters.flatMap((filter) => {
    if (!filter || typeof filter !== 'object') return [];
    const rec = filter as Record<string, unknown>;
    const members = typeof rec.member === 'string' ? [rec.member] : [];
    return [
      ...members,
      ...extractFilterMembers(Array.isArray(rec.and) ? rec.and : []),
      ...extractFilterMembers(Array.isArray(rec.or) ? rec.or : []),
    ];
  });
}

function hasDateRange(dateRange: unknown): boolean {
  if (typeof dateRange === 'string') return dateRange.trim().length > 0;
  if (!Array.isArray(dateRange) || dateRange.length !== 2) return false;
  return dateRange.every((value) => typeof value === 'string' && value.trim().length > 0);
}
