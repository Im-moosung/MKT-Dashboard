import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { QueryBuilder } from '@/components/builder/QueryBuilder';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      cubes: [
        {
          name: 'AdsCampaign',
          measures: [{ name: 'AdsCampaign.spend', title: '스펜드' }],
          dimensions: [
            { name: 'AdsCampaign.branchId', title: '지점', type: 'string' },
            { name: 'AdsCampaign.reportDate', title: '보고일', type: 'time' },
          ],
        },
        {
          name: 'Orders',
          measures: [{ name: 'Orders.count', title: '주문수' }],
          dimensions: [{ name: 'Orders.branchId', title: '주문 지점', type: 'string' }],
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

  it('shows only time dimensions in the period selector', async () => {
    render(<QueryBuilder onChange={() => {}} />);

    await waitFor(() => {
      expect(screen.queryByText('메타 정보 불러오는 중…')).toBeNull();
    });

    const options = Array.from(screen.getByLabelText('기간 필드').querySelectorAll('option')).map(
      (option) => option.textContent,
    );
    expect(options).toContain('보고일');
    expect(options).not.toContain('지점');
    expect(options).not.toContain('주문 지점');
  });

  it('labels demo or incomplete data sources in member buttons', async () => {
    render(<QueryBuilder onChange={() => {}} />);

    await waitFor(() => {
      expect(screen.queryByText('메타 정보 불러오는 중…')).toBeNull();
    });

    expect(screen.getByText('주문수 · 데모')).not.toBeNull();
    expect(screen.getByText('스펜드 · 부분 실데이터')).not.toBeNull();
  });
});
