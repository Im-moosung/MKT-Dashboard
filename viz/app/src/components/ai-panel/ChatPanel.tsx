'use client';
import { useState, useEffect } from 'react';
import { MessageList, type Message } from './MessageList';
import { Composer } from './Composer';

interface ChartRow {
  id: string;
  title: string;
  gridX: number;
  gridY: number;
  gridW: number;
  gridH: number;
  cubeQueryJson: unknown;
  chartConfigJson: unknown;
}

interface ChatPanelProps {
  dashboardId: string;
  onChartAdded: (chart: ChartRow) => void;
}

export function ChatPanel({ dashboardId, onChartAdded }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  // Load existing chat history on mount
  useEffect(() => {
    fetch(`/api/dashboards/${dashboardId}/chat`)
      .then((r) => r.json())
      .then((body: { messages?: { role: string; content: string; createdAt: string }[] }) => {
        if (body.messages) {
          setMessages(
            body.messages.map((m) => ({
              role: m.role as 'user' | 'assistant',
              content: m.content,
              timestamp: m.createdAt,
            })),
          );
        }
      })
      .catch(() => {
        // silently ignore — history load failure is non-critical
      });
  }, [dashboardId]);

  async function handleSubmit(text: string) {
    const userMsg: Message = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const aiRes = await fetch('/api/ai/create-chart', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ prompt: text, dashboardId }),
      });

      if (!aiRes.ok) {
        const errBody = await aiRes.json().catch(() => ({}));
        const errMsg =
          (errBody as { error?: string }).error ?? 'AI 응답 실패, 다시 시도해 주세요. 또는 수동 빌더를 사용하세요.';
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: errMsg },
        ]);
        return;
      }

      const { response } = (await aiRes.json()) as {
        response: {
          title: string;
          cubeQuery: unknown;
          chartConfig: { type: string };
        };
        data: Record<string, unknown>[];
      };

      // Save chart to DB
      const chartRes = await fetch('/api/charts', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          dashboardId,
          title: response.title,
          cubeQueryJson: response.cubeQuery,
          chartConfigJson: response.chartConfig,
          source: 'ai',
          promptHistoryJson: [text],
          gridX: 0,
          gridY: 999,
          gridW: 6,
          gridH: 4,
        }),
      });

      if (!chartRes.ok) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '차트 저장에 실패했습니다. 다시 시도해 주세요.' },
        ]);
        return;
      }

      const { chart } = (await chartRes.json()) as { chart: ChartRow };

      // 데이터 로드는 부모 dashboard-client.handleChartAdded에서 처리. 여기서 중복 호출 불필요.
      onChartAdded({ ...chart, cubeQueryJson: chart.cubeQueryJson ?? response.cubeQuery });

      const assistantMsg: Message = {
        role: 'assistant',
        content: `✓ 차트 추가됨: ${chart.title}`,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '네트워크 오류가 발생했습니다.' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside
      className="w-80 border-l flex flex-col bg-background h-full"
      data-testid="chat-panel"
    >
      <div className="p-3 border-b">
        <h2 className="text-sm font-semibold">AI 차트 생성</h2>
      </div>
      <MessageList messages={messages} />
      <Composer onSubmit={handleSubmit} disabled={loading} />
    </aside>
  );
}
