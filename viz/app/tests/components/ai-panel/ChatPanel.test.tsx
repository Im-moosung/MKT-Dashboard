import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ChatPanel } from '@/components/ai-panel/ChatPanel';

// Mock fetch globally
const fetchMock = vi.fn();
global.fetch = fetchMock;

// Stub loadCubeData
vi.mock('@/lib/cube-client', () => ({
  loadCubeData: vi.fn().mockResolvedValue({ data: [] }),
}));

beforeEach(() => {
  fetchMock.mockReset();
});

describe('ChatPanel', () => {
  it('renders panel with header', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ messages: [] }),
    });

    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={vi.fn()} />);
    expect(screen.getByTestId('chat-panel')).not.toBeNull();
    expect(screen.getByText('AI 차트 생성')).not.toBeNull();
  });

  it('shows empty state message when no messages', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ messages: [] }),
    });

    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText(/AI에게 차트를 요청해 보세요/)).not.toBeNull();
    });
  });

  it('loads existing messages on mount', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        messages: [
          { role: 'user', content: '안녕하세요', createdAt: '2026-01-01T00:00:00Z' },
          { role: 'assistant', content: '✓ 차트 추가됨: 테스트', createdAt: '2026-01-01T00:00:01Z' },
        ],
      }),
    });

    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('안녕하세요')).not.toBeNull();
      expect(screen.getByText('✓ 차트 추가됨: 테스트')).not.toBeNull();
    });
  });

  it('calls onChartAdded after single /api/ai/create-chart call returns chart', async () => {
    // 1) GET initial chat
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ messages: [] }),
    });
    // 2) POST /api/ai/create-chart — server now returns the persisted chart in one shot
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        chart: {
          id: 'chart-uuid',
          title: '채널별 지출',
          gridX: 0,
          gridY: 999,
          gridW: 6,
          gridH: 4,
          cubeQueryJson: { measures: ['AdsCampaign.spend'], dimensions: [] },
          chartConfigJson: { type: 'bar' },
        },
        response: {
          title: '채널별 지출',
          cubeQuery: { measures: ['AdsCampaign.spend'], dimensions: [] },
          chartConfig: { type: 'bar' },
        },
        data: [],
      }),
    });

    const onChartAdded = vi.fn();
    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={onChartAdded} />);

    const textarea = screen.getByTestId('composer-textarea');
    await act(async () => {
      fireEvent.change(textarea, { target: { value: '채널별 지출 막대 차트' } });
    });
    fireEvent.click(screen.getByTestId('composer-submit'));

    await waitFor(() => {
      expect(onChartAdded).toHaveBeenCalledOnce();
      expect(screen.getByText('✓ 차트 추가됨: 채널별 지출')).not.toBeNull();
    });

    // Ensure the component does NOT call a separate /api/charts endpoint.
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.some((u) => u.includes('/api/charts') && !u.includes('/create-chart'))).toBe(false);
  });

  it('maps cube_failed to Korean Cube error and does not call onChartAdded', async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) });
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => ({ errorCode: 'cube_failed', error: 'data layer failed' }),
    });

    const onChartAdded = vi.fn();
    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={onChartAdded} />);

    const textarea = screen.getByTestId('composer-textarea');
    await act(async () => {
      fireEvent.change(textarea, { target: { value: '차트 요청' } });
    });
    fireEvent.click(screen.getByTestId('composer-submit'));

    await waitFor(() => {
      expect(screen.getByText(/Cube.*실패|데이터 조회에 실패/)).not.toBeNull();
    });
    expect(onChartAdded).not.toHaveBeenCalled();
  });

  it('maps claude_failed to Korean AI error message', async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) });
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => ({ errorCode: 'claude_failed', error: 'claude api error' }),
    });

    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={vi.fn()} />);
    const textarea = screen.getByTestId('composer-textarea');
    await act(async () => {
      fireEvent.change(textarea, { target: { value: '차트 요청' } });
    });
    fireEvent.click(screen.getByTestId('composer-submit'));

    await waitFor(() => {
      expect(screen.getByText(/AI 응답.*실패|AI가 응답하지 못했/)).not.toBeNull();
    });
  });

  it('maps persist_failed to Korean persistence error message', async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) });
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ errorCode: 'persist_failed', error: 'db insert failed' }),
    });

    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={vi.fn()} />);
    const textarea = screen.getByTestId('composer-textarea');
    await act(async () => {
      fireEvent.change(textarea, { target: { value: '차트 요청' } });
    });
    fireEvent.click(screen.getByTestId('composer-submit'));

    await waitFor(() => {
      expect(screen.getByText(/차트 저장.*실패/)).not.toBeNull();
    });
  });

  it('falls back to generic Korean message when no errorCode provided', async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) });
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
    });

    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={vi.fn()} />);
    const textarea = screen.getByTestId('composer-textarea') as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(textarea, { target: { value: '차트 요청' } });
    });
    fireEvent.click(screen.getByTestId('composer-submit'));

    await waitFor(() => {
      expect(screen.getByText(/다시 시도해 주세요/)).not.toBeNull();
    });
  });
});
