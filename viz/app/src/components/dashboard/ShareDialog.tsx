'use client';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface ShareDialogProps {
  dashboardId: string;
}

export function ShareDialog({ dashboardId }: ShareDialogProps) {
  const [open, setOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleCreateLink() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/dashboards/${dashboardId}/share`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError((body as { error?: string }).error ?? '링크 생성에 실패했습니다.');
        return;
      }
      const { url } = (await res.json()) as { token: string; url: string };
      setShareUrl(url);
    } catch {
      setError('링크 생성에 실패했습니다. 네트워크 오류.');
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('클립보드 복사에 실패했습니다.');
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (!nextOpen) {
      setShareUrl(null);
      setError(null);
      setCopied(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button variant="outline" size="sm" data-testid="share-trigger" />}>
        공유
      </DialogTrigger>
      <DialogContent className="max-w-md w-full" aria-label="대시보드 공유">
        <DialogHeader>
          <DialogTitle>대시보드 공유</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <p className="text-xs text-muted-foreground">
            POC 기간 동안 만료 없음. 링크를 받은 @dstrict.com 계정이 읽기 전용으로 접근 가능.
          </p>

          {!shareUrl ? (
            <Button
              onClick={handleCreateLink}
              disabled={loading}
              data-testid="share-create-btn"
            >
              {loading ? '생성 중…' : '공유 링크 생성'}
            </Button>
          ) : (
            <div className="flex gap-2 items-center">
              <Input
                readOnly
                value={shareUrl}
                className="flex-1 text-xs"
                data-testid="share-url-input"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                data-testid="share-copy-btn"
              >
                {copied ? '복사됨' : '복사'}
              </Button>
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive" data-testid="share-error">{error}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
