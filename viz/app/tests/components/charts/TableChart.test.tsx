import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { TableChart } from '@/components/charts/TableChart';

describe('TableChart', () => {
  it('renders container with data-chart="table" and shows rows', () => {
    const { container, getByText } = render(
      <TableChart data={[{ date: '2026-04-01', spend: 100 }]} config={{ type: 'table' }} />
    );
    expect(container.querySelector('[data-chart="table"]')).not.toBeNull();
    expect(getByText('2026-04-01')).toBeTruthy();
  });
});
