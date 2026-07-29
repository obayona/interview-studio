import { render, screen } from '@testing-library/react';
import axe from 'axe-core';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SettingsPage } from './SettingsPage';

describe('SettingsPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('loads configured status and capability warnings', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith('/api/v1/capabilities')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              interview: {
                available: false,
                reason: 'OpenAI API key is not configured',
              },
              speech_to_text: { available: false, reason: 'Enable STT' },
              text_to_speech: { available: false, reason: 'Enable TTS' },
            }),
            { status: 200 },
          ),
        );
      }
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
    expect(
      screen.getByText(/Interview controls remain unavailable/),
    ).toBeVisible();
    const accessibility = await axe.run(container, {
      rules: { 'color-contrast': { enabled: false } },
    });
    expect(accessibility.violations).toEqual([]);
  });
});
