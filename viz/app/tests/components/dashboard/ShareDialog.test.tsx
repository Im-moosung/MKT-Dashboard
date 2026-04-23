import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShareDialog } from '@/components/dashboard/ShareDialog';

// next-intl mock not needed for ShareDialog since it doesn't use useTranslations
// but layout provider is needed if any child does — here ShareDialog has none

const fetchMock = vi.fn();
global.fetch = fetchMock;

beforeEach(() => {
  fetchMock.mockReset();
});

describe('ShareDialog', () => {
  it('renders the share trigger button', () => {
    render(<ShareDialog dashboardId="test-dashboard-id" />);
    expect(screen.getByTestId('share-trigger')).not.toBeNull();
  });

  it('opens dialog when trigger is clicked and shows create link button', async () => {
    render(<ShareDialog dashboardId="test-dashboard-id" />);
    fireEvent.click(screen.getByTestId('share-trigger'));
    await waitFor(() => {
      expect(screen.getByTestId('share-create-btn')).not.toBeNull();
    });
  });

  it('calls POST /api/dashboards/[id]/share and displays url on success', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        token: 'abc123',
        url: 'http://localhost:3000/shared/abc123',
      }),
    });

    render(<ShareDialog dashboardId="test-dashboard-id" />);
    fireEvent.click(screen.getByTestId('share-trigger'));
    await waitFor(() => screen.getByTestId('share-create-btn'));

    fireEvent.click(screen.getByTestId('share-create-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('share-url-input')).not.toBeNull();
      const input = screen.getByTestId('share-url-input') as HTMLInputElement;
      expect(input.value).toBe('http://localhost:3000/shared/abc123');
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/dashboards/test-dashboard-id/share',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('shows error message when API call fails', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'unauthorized' }),
    });

    render(<ShareDialog dashboardId="test-dashboard-id" />);
    fireEvent.click(screen.getByTestId('share-trigger'));
    await waitFor(() => screen.getByTestId('share-create-btn'));

    fireEvent.click(screen.getByTestId('share-create-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('share-error')).not.toBeNull();
    });
  });
});
