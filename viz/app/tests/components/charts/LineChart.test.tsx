import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { LineChart } from '@/components/charts/LineChart';

describe('LineChart', () => {
  it('renders an svg with data-chart="line"', () => {
    const { container } = render(
      <LineChart data={[{ date: '2026-04-01', spend: 100 }, { date: '2026-04-02', spend: 150 }]}
        config={{ type: 'line', x: 'date', y: 'spend', title: '테스트' }} />
    );
    expect(container.querySelector('[data-chart="line"]')).not.toBeNull();
  });
});
