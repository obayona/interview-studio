import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { HeaderAvatar } from './HeaderAvatar';

describe('HeaderAvatar', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('links to the profile and shows the placeholder when no avatar is set', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              id: 'default',
              full_name: '',
              headline: '',
              summary: '',
              location: '',
              email: '',
              phone: '',
              skills: [],
              seniority: '',
              availability: '',
              links: [],
              experiences: [],
              projects: [],
              avatar_url: null,
              created_at: '2026-07-29T00:00:00Z',
              updated_at: '2026-07-29T00:00:00Z',
            }),
            { status: 200 },
          ),
        ),
      ),
    );

    const { container } = render(<HeaderAvatar />);
    const link = await screen.findByRole('link', { name: 'Open profile' });

    expect(link).toHaveAttribute('href', '/profile');
    expect(
      container.querySelector('.app-shell__avatar .ui-icon'),
    ).not.toBeNull();
    expect(container.querySelector('.app-shell__avatar img')).toBeNull();
  });
});
