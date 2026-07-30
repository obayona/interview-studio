import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
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
              {
                key: 'chat_model',
                configured: false,
                value: 'gpt-4o-mini',
                options: ['gpt-4o-mini', 'gpt-4.1'],
              },
              {
                key: 'transcription_model',
                configured: false,
                value: 'gpt-4o-mini-transcribe',
                options: [
                  'gpt-4o-mini-transcribe',
                  'gpt-4o-transcribe',
                  'whisper-1',
                ],
              },
              {
                key: 'speech_model',
                configured: false,
                value: 'gpt-4o-mini-tts',
                options: ['gpt-4o-mini-tts', 'tts-1'],
              },
              {
                key: 'vision_model',
                configured: false,
                value: 'gpt-4o-mini',
                options: ['gpt-4o-mini', 'gpt-4.1'],
              },
              {
                key: 'voice',
                configured: false,
                value: 'marin',
                options: ['marin', 'cedar', 'alloy'],
              },
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
    fireEvent.click(
      screen.getByRole('button', { name: /Advanced model parameters/ }),
    );
    expect(screen.getByLabelText('Chat model')).toHaveValue('gpt-4o-mini');
    expect(screen.getByLabelText('Chat model').tagName).toBe('SELECT');
    expect(screen.getByLabelText('Transcription model').tagName).toBe('SELECT');
    expect(screen.getByLabelText('Speech model').tagName).toBe('SELECT');
    expect(screen.getByLabelText('Vision model').tagName).toBe('SELECT');
    expect(screen.getByLabelText('Voice')).toHaveValue('marin');
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

  it('autosaves switches without requiring the Save button', async () => {
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      const settings = [
        { key: 'api_key', configured: false, value: null },
        { key: 'chat_model', configured: true, value: 'gpt-4o-mini' },
        { key: 'tts_enabled', configured: true, value: 'false' },
        { key: 'stt_enabled', configured: true, value: 'false' },
        { key: 'theme', configured: true, value: 'system' },
      ];
      if (init?.method === 'PATCH') {
        const update = JSON.parse(String(init.body)) as {
          tts_enabled: boolean;
        };
        settings.find((item) => item.key === 'tts_enabled')!.value = String(
          update.tts_enabled,
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ settings }), { status: 200 }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<SettingsPage />);
    fireEvent.click(
      await screen.findByRole('switch', { name: 'Voice responses' }),
    );

    await waitFor(
      () => {
        const patch = fetchMock.mock.calls.find(
          ([, init]) => init?.method === 'PATCH',
        );
        expect(JSON.parse(String(patch?.[1]?.body))).toMatchObject({
          tts_enabled: true,
        });
      },
      { timeout: 2000 },
    );
    expect(screen.queryByRole('button', { name: 'Discard' })).toBeNull();
  });

  it('disables an explicit Save button while the request is pending', async () => {
    let finishSave: ((response: Response) => void) | undefined;
    const pendingSave = new Promise<Response>((resolve) => {
      finishSave = resolve;
    });
    const settings = [
      { key: 'api_key', configured: false, value: null },
      { key: 'chat_model', configured: true, value: 'gpt-4o-mini' },
      { key: 'theme', configured: true, value: 'system' },
    ];
    vi.stubGlobal(
      'fetch',
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) =>
        init?.method === 'PATCH'
          ? pendingSave
          : Promise.resolve(
              new Response(JSON.stringify({ settings }), { status: 200 }),
            ),
      ),
    );

    render(<SettingsPage />);
    fireEvent.change(await screen.findByLabelText('Theme'), {
      target: { value: 'dark' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    expect(
      await screen.findByRole('button', { name: 'Saving…' }),
    ).toBeDisabled();
    finishSave!(
      new Response(
        JSON.stringify({
          settings: settings.map((item) =>
            item.key === 'theme' ? { ...item, value: 'dark' } : item,
          ),
        }),
        { status: 200 },
      ),
    );
    expect(await screen.findByText('Settings saved.')).toBeVisible();
  });
});
