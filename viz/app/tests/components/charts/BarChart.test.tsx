import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { BarChart } from '@/components/charts/BarChart';

describe('BarChart', () => {
  it('renders container with data-chart="bar"', () => {
    const { container } = render(
      <BarChart data={[{ channel: 'META', spend: 200 }]}
        config={{ type: 'bar', x: 'channel', y: 'spend' }} />
    );
    expect(container.querySelector('[data-chart="bar"]')).not.toBeNull();
  });
});
