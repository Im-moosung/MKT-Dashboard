// Intl 포맷 공용 helper — ko-KR 기본. 차트·KPI·UI 전반에서 재사용.

const dateFormatter = new Intl.DateTimeFormat('ko-KR', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

const dateTimeFormatter = new Intl.DateTimeFormat('ko-KR', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});

const numberFormatter = new Intl.NumberFormat('ko-KR');

const CURRENCY_FORMATTERS: Record<string, Intl.NumberFormat> = {};

function getCurrencyFormatter(currency: string) {
  if (!CURRENCY_FORMATTERS[currency]) {
    CURRENCY_FORMATTERS[currency] = new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    });
  }
  return CURRENCY_FORMATTERS[currency];
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = value instanceof Date ? value : new Date(value);
  if (isNaN(d.getTime())) return String(value);
  return dateFormatter.format(d);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = value instanceof Date ? value : new Date(value);
  if (isNaN(d.getTime())) return String(value);
  return dateTimeFormatter.format(d);
}

export function formatNumber(value: unknown): string {
  const n = Number(value);
  if (isNaN(n)) return String(value ?? '—');
  return numberFormatter.format(n);
}

export function formatCurrency(value: unknown, currency = 'KRW'): string {
  const n = Number(value);
  if (isNaN(n)) return String(value ?? '—');
  return getCurrencyFormatter(currency).format(n);
}

export function formatPercent(value: unknown, fractionDigits = 1): string {
  const n = Number(value);
  if (isNaN(n)) return String(value ?? '—');
  return `${n.toFixed(fractionDigits)}%`;
}
