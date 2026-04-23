import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { VegaLiteChart } from '@/components/charts/VegaLiteChart';

describe('VegaLiteChart', () => {
  it('renders container with data-chart="vega"', () => {
    const spec = {
      $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
      mark: 'bar',
      encoding: { x: { field: 'a', type: 'ordinal' }, y: { field: 'b', type: 'quantitative' } },
    };
    const { container } = render(
      <VegaLiteChart data={[{ a: 'x', b: 1 }]} config={{ type: 'vega', spec }} />
    );
    expect(container.querySelector('[data-chart="vega"]')).not.toBeNull();
  });
});
