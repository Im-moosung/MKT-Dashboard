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

  it('calls onChartAdded after successful AI + chart save flow', async () => {
    // 1) GET /api/dashboards/.../chat (initial load)
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ messages: [] }),
    });
    // 2) POST /api/ai/create-chart
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        response: {
          title: '채널별 지출',
          cubeQuery: { measures: ['Spend.total'], dimensions: [] },
          chartConfig: { type: 'bar' },
        },
        data: [],
      }),
    });
    // 3) POST /api/charts
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
          cubeQueryJson: { measures: ['Spend.total'], dimensions: [] },
          chartConfigJson: { type: 'bar' },
        },
      }),
    });

    const onChartAdded = vi.fn();
    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={onChartAdded} />);

    const textarea = screen.getByTestId('composer-textarea');
    fireEvent.change(textarea, { target: { value: '채널별 지출 막대 차트' } });
    fireEvent.click(screen.getByTestId('composer-submit'));

    await waitFor(() => {
      expect(onChartAdded).toHaveBeenCalledOnce();
      expect(screen.getByText('✓ 차트 추가됨: 채널별 지출')).not.toBeNull();
    });
  });

  it('shows error message when AI call fails', async () => {
    // 1) GET initial chat
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ messages: [] }),
    });
    // 2) POST ai/create-chart fails
    fetchMock.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'AI 응답 실패, 다시 시도해 주세요' }),
    });

    render(<ChatPanel dashboardId="test-dash-id" onChartAdded={vi.fn()} />);

    const textarea = screen.getByTestId('composer-textarea') as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(textarea, { target: { value: '차트 요청' } });
    });
    expect(textarea.value).toBe('차트 요청');
    fireEvent.click(screen.getByTestId('composer-submit'));

    await waitFor(() => {
      expect(screen.getByText('AI 응답 실패, 다시 시도해 주세요')).not.toBeNull();
    });
  });
});
