'use client';
import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm px-4 text-center">
        AI에게 차트를 요청해 보세요.
        <br />
        예) &ldquo;지난 30일 채널별 지출 막대 차트&rdquo;
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
      {messages.map((msg, idx) => (
        <div
          key={idx}
          className={cn(
            'max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap break-words',
            msg.role === 'user'
              ? 'self-end bg-primary text-primary-foreground'
              : 'self-start bg-muted text-muted-foreground',
          )}
        >
          {msg.content}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
