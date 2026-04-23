import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { ChartTypePicker } from '@/components/builder/ChartTypePicker';

describe('ChartTypePicker', () => {
  it('renders 5 chart type buttons', () => {
    const { getByTestId } = render(
      <ChartTypePicker value="line" onChange={() => {}} />,
    );
    for (const type of ['line', 'bar', 'kpi', 'table', 'pie']) {
      expect(getByTestId(`chart-type-${type}`)).not.toBeNull();
    }
  });

  it('calls onChange with correct type on click', () => {
    const onChange = vi.fn();
    const { getByTestId } = render(
      <ChartTypePicker value="line" onChange={onChange} />,
    );
    fireEvent.click(getByTestId('chart-type-bar'));
    expect(onChange).toHaveBeenCalledWith('bar');
  });

  it('highlights selected type with default variant', () => {
    const { getByTestId } = render(
      <ChartTypePicker value="pie" onChange={() => {}} />,
    );
    const pieBtn = getByTestId('chart-type-pie');
    // default variant buttons don't have 'outline' in class
    expect(pieBtn.className).not.toContain('border-border');
  });
});
