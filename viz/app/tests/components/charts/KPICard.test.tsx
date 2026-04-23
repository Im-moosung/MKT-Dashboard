import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { KPICard } from '@/components/charts/KPICard';

describe('KPICard', () => {
  it('renders container with data-chart="kpi" and displays value', () => {
    const { container, getByText } = render(
      <KPICard data={[{ spend: 12345 }]} config={{ type: 'kpi', y: 'spend' }} />
    );
    expect(container.querySelector('[data-chart="kpi"]')).not.toBeNull();
    expect(getByText('12,345')).toBeTruthy();
  });
});
