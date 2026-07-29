import { cleanup, render, screen, waitFor } from '@testing-library/react';
import axe from 'axe-core';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SettingsPage } from './SettingsPage';

describe('SettingsPage', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('loads settings without requesting capabilities', async () => {
    const fetchMock = vi.fn(() => {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            settings: [
              { key: 'api_key', configured: false, value: null },
              { key: 'chat_model', configured: false, value: 'gpt-4o-mini' },
              { key: 'theme', configured: false, value: 'system' },
            ],
          }),
          { status: 200 },
        ),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    const { container } = render(<SettingsPage />);

    expect(
      await screen.findByRole('heading', { name: 'OpenAI' }),
    ).toBeVisible();
    expect(screen.getByLabelText('API key')).toHaveAttribute(
      'placeholder',
      'sk-…',
    );
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/settings',
      expect.anything(),
    );
    const accessibility = await axe.run(container, {
      rules: { 'color-contrast': { enabled: false } },
    });
    expect(accessibility.violations).toEqual([]);
  });

  it('displays a fixed mask for a configured API key', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              settings: [
                {
                  key: 'api_key',
                  configured: true,
                  masked_suffix: '1234',
                },
              ],
            }),
            { status: 200 },
          ),
        );
      }),
    );

    render(<SettingsPage />);

    const input = await screen.findByLabelText('API key');
    await waitFor(() =>
      expect(input).toHaveAttribute('placeholder', '********'),
    );
    expect(input).toHaveValue('');
    expect(
      screen.queryByPlaceholderText('Leave blank to keep the current key'),
    ).not.toBeInTheDocument();
  });
});
