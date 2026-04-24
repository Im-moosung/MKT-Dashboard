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

type ErrorCode = 'cube_failed' | 'claude_failed' | 'persist_failed';

const ERROR_MESSAGES: Record<ErrorCode, string> = {
  cube_failed: '데이터 조회에 실패했습니다. 잠시 후 다시 시도하거나 수동 빌더를 사용하세요.',
  claude_failed: 'AI가 응답하지 못했습니다. 다시 시도해 주세요.',
  persist_failed: '차트 저장에 실패했습니다. 다시 시도해 주세요.',
};
const FALLBACK_ERROR = '요청을 처리하지 못했습니다. 다시 시도해 주세요.';

export function ChatPanel({ dashboardId, onChartAdded }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

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
      const res = await fetch('/api/ai/create-chart', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ prompt: text, dashboardId }),
      });

      if (!res.ok) {
        const errBody = (await res.json().catch(() => ({}))) as {
          errorCode?: ErrorCode;
          error?: string;
        };
        const code = errBody.errorCode;
        const content =
          (code && ERROR_MESSAGES[code]) ?? errBody.error ?? FALLBACK_ERROR;
        setMessages((prev) => [...prev, { role: 'assistant', content }]);
        return;
      }

      const { chart } = (await res.json()) as { chart: ChartRow };
      onChartAdded(chart);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `✓ 차트 추가됨: ${chart.title}` },
      ]);
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
