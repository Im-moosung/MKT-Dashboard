import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Mock next-intl globally so components using useTranslations work in tests
// without needing NextIntlClientProvider.
vi.mock('next-intl', () => ({
  useTranslations: (namespace: string) => (key: string) => {
    const messages: Record<string, Record<string, string>> = {
      common: {
        save: '저장',
        cancel: '취소',
        delete: '삭제',
        edit: '편집',
        share: '공유',
        loading: '로딩 중…',
        error: '오류가 발생했습니다',
        retry: '다시 시도',
        close: '닫기',
        submit: '전송',
      },
    };
    return messages[namespace]?.[key] ?? key;
  },
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
}));
