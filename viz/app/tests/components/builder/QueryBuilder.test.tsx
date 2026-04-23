import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { QueryBuilder } from '@/components/builder/QueryBuilder';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      cubes: [
        {
          name: 'AdsCampaign',
          measures: [{ name: 'AdsCampaign.spend', title: '스펜드' }],
          dimensions: [{ name: 'AdsCampaign.branchId', title: '지점' }],
        },
      ],
    }),
  }));
});

describe('QueryBuilder', () => {
  it('shows loading state initially then resolves', async () => {
    const { getByText, queryByText } = render(
      <QueryBuilder onChange={() => {}} />,
    );
    expect(getByText('메타 정보 불러오는 중…')).not.toBeNull();
    await waitFor(() => {
      expect(queryByText('메타 정보 불러오는 중…')).toBeNull();
    });
  });

  it('calls onChange when chart type changes', async () => {
    const onChange = vi.fn();
    const { getByTestId, queryByText } = render(
      <QueryBuilder onChange={onChange} />,
    );
    await waitFor(() => {
      expect(queryByText('메타 정보 불러오는 중…')).toBeNull();
    });
    const barBtn = getByTestId('chart-type-bar');
    barBtn.click();
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.chartType).toBe('bar');
  });
});
