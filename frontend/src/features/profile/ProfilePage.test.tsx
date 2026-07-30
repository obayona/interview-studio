import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import axe from 'axe-core';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ProfilePage } from './ProfilePage';

vi.mock('../../components/ui/Dialog', () => ({
  Dialog: ({ open, children }: { open: boolean; children: ReactNode }) => (
    <div hidden={!open}>{children}</div>
  ),
}));

const profile = {
  id: 'default',
  full_name: 'Taylor Example',
  headline: 'Software Engineer',
  summary: 'Builds useful software.',
  location: 'Quito, Ecuador',
  email: 'taylor@example.com',
  phone: '',
  skills: ['Python'],
  seniority: 'Senior',
  availability: '',
  links: [],
  experiences: [],
  projects: [],
  avatar_url: null,
  created_at: '2026-07-29T00:00:00Z',
  updated_at: '2026-07-29T00:00:00Z',
};

describe('ProfilePage', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('loads the aggregate and autosaves edited fields', async () => {
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as typeof profile;
        return Promise.resolve(
          new Response(JSON.stringify({ ...profile, ...body }), {
            status: 200,
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify(profile), { status: 200 }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    const { container } = render(<ProfilePage />);
    const name = await screen.findByLabelText('Name');
    fireEvent.change(name, { target: { value: 'Updated Name' } });

    await waitFor(
      () => {
        const patch = fetchMock.mock.calls.find(
          ([, init]) => init?.method === 'PATCH',
        );
        expect(patch).toBeDefined();
        expect(JSON.parse(String(patch?.[1]?.body))).toMatchObject({
          full_name: 'Updated Name',
        });
      },
      { timeout: 2000 },
    );
    expect(await screen.findByText('All changes saved')).toBeVisible();
    const accessibility = await axe.run(container, {
      rules: { 'color-contrast': { enabled: false } },
    });
    expect(accessibility.violations).toEqual([]);
  });

  it('shows a retryable error when the profile cannot load', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({ code: 'failed', message: 'Profile unavailable' }),
            { status: 500 },
          ),
        ),
      ),
    );

    render(<ProfilePage />);

    expect(await screen.findByText('Profile unavailable')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeVisible();
  });

  it('imports a CV through a modal without retaining the file', async () => {
    let finishImport: ((response: Response) => void) | undefined;
    const importResponse = new Promise<Response>((resolve) => {
      finishImport = resolve;
    });
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const path = String(input);
        if (path.endsWith('/cv/import')) return importResponse;
        return Promise.resolve(
          new Response(JSON.stringify(profile), { status: 200 }),
        );
      }),
    );

    const { container } = render(<ProfilePage />);
    await screen.findByLabelText('Name');
    fireEvent.click(screen.getByRole('button', { name: 'Import profile' }));
    expect(
      screen.getByText(/Choose a PDF CV to populate your editable profile/),
    ).toBeVisible();
    expect(screen.getByText(/The file is not stored/)).toBeVisible();
    const input = container.querySelector<HTMLInputElement>(
      'input[accept="application/pdf,.pdf"]',
    );
    expect(input).not.toBeNull();
    fireEvent.change(input!, {
      target: {
        files: [
          new File(['%PDF resume'], 'resume.pdf', {
            type: 'application/pdf',
          }),
        ],
      },
    });
    expect(screen.getByText('resume.pdf')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Import' }));

    expect(await screen.findByText('Importing profile')).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent(
      'Importing profile information from CV',
    );
    expect(
      screen.getByText(/Extracting your profile, skills, and work experience/),
    ).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull();

    finishImport!(
      new Response(
        JSON.stringify({
          full_name: 'Imported Name',
          headline: null,
          summary: null,
          location: null,
          email: null,
          phone: null,
          skills: [],
          experiences: [],
          projects: [],
        }),
        { status: 200 },
      ),
    );
    await waitFor(() =>
      expect(screen.queryByText('Importing profile')).toBeNull(),
    );
    expect(screen.getByLabelText('Name')).toHaveValue('Imported Name');
    expect(screen.getByText('Profile imported from CV.')).toBeVisible();
  });
});
