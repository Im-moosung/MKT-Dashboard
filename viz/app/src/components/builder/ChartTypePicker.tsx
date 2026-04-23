'use client';
import { Button } from '@/components/ui/button';
import type { PresetChartType } from '@/lib/chart-types/registry';

const CHART_OPTIONS: { type: PresetChartType; label: string }[] = [
  { type: 'line', label: '선형' },
  { type: 'bar', label: '막대' },
  { type: 'kpi', label: 'KPI' },
  { type: 'table', label: '표' },
  { type: 'pie', label: '원형' },
];

export function ChartTypePicker({
  value,
  onChange,
}: {
  value: PresetChartType;
  onChange: (type: PresetChartType) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {CHART_OPTIONS.map((opt) => (
        <Button
          key={opt.type}
          size="sm"
          variant={value === opt.type ? 'default' : 'outline'}
          onClick={() => onChange(opt.type)}
          data-testid={`chart-type-${opt.type}`}
        >
          {opt.label}
        </Button>
      ))}
    </div>
  );
}
