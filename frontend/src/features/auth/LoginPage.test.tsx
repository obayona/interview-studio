import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { LoginPage } from './LoginPage';

describe('LoginPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('provides an accessible sign-in form and reports rejected credentials', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 'authentication_failed',
          message: 'The username or password is incorrect.',
          field_errors: {},
          request_id: 'request-1',
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText('Username'), {
      target: { value: 'owner' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrong' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'The username or password is incorrect.',
      ),
    );
  });
});
