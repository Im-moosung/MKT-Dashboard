import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { PieChart } from '@/components/charts/PieChart';

describe('PieChart', () => {
  it('renders container with data-chart="pie"', () => {
    const { container } = render(
      <PieChart data={[{ channel: 'META', spend: 50 }]}
        config={{ type: 'pie', x: 'channel', y: 'spend' }} />
    );
    expect(container.querySelector('[data-chart="pie"]')).not.toBeNull();
  });
});
