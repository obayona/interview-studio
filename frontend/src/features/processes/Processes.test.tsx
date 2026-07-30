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
import { ProcessDetail } from './ProcessDetail';
import { ProcessForm } from './ProcessForm';
import { ProcessList } from './ProcessList';
import { newStageConfiguration } from './defaults';

vi.mock('../../components/ui/Dialog', () => ({
  Dialog: ({ open, children }: { open: boolean; children: ReactNode }) => (
    <div hidden={!open}>{children}</div>
  ),
}));

const process = {
  id: 'process-1',
  title: 'Backend role',
  company_name: 'Example Co',
  target_role: 'Senior Backend Engineer',
  job_description: 'Build reliable APIs.',
  company_info: 'Developer tools.',
  job_source_url: null,
  company_source_url: null,
  status: 'active',
  stages: [
    {
      id: 'stage-1',
      stage_type: 'technical',
      position: 0,
      enabled: true,
      status: 'in_progress',
      configuration: newStageConfiguration(),
      attempts: [
        {
          id: 'attempt-1',
          attempt_number: 1,
          status: 'ready',
          started_at: null,
          ended_at: null,
          termination_reason: null,
          created_at: '2026-07-29T00:00:00Z',
        },
      ],
    },
  ],
  created_at: '2026-07-29T00:00:00Z',
  updated_at: '2026-07-29T00:00:00Z',
};

describe('process pages', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.replaceState({}, '', '/');
  });

  it('lists processes with progress and detail navigation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: process.id,
                title: process.title,
                company_name: process.company_name,
                target_role: process.target_role,
                status: process.status,
                stage_count: 2,
                completed_stage_count: 1,
                attempt_count: 3,
                updated_at: process.updated_at,
              },
            ]),
            { status: 200 },
          ),
        ),
      ),
    );

    const { container } = render(<ProcessList />);
    const link = await screen.findByRole('link', { name: /Backend role/ });
    expect(link).toHaveAttribute('href', '/processes/details?id=process-1');
    expect(screen.getByText('1 of 2 stages')).toBeVisible();
    expect(screen.getByText('3 attempts')).toBeVisible();
    fireEvent.change(screen.getByRole('searchbox'), {
      target: { value: 'missing process' },
    });
    expect(link).toBeVisible();
    expect(
      await screen.findByText('No matching processes', undefined, {
        timeout: 1000,
      }),
    ).toBeVisible();
    expect(
      (
        await axe.run(container, {
          rules: { 'color-contrast': { enabled: false } },
        })
      ).violations,
    ).toEqual([]);
  });

  it('shows all ordered default stages, including skipped stages', () => {
    render(<ProcessForm mode="create" />);

    expect(screen.getByText('1. Screening')).toBeVisible();
    expect(screen.getByText('2. Behavioral')).toBeVisible();
    expect(screen.getByText('3. Technical / experience')).toBeVisible();
    expect(screen.getByText('4. System design')).toBeVisible();
    expect(
      screen.getByRole('switch', { name: 'Include System design' }),
    ).toHaveAttribute('aria-checked', 'false');
  });

  it('autosaves switches only when editing an existing process', async () => {
    window.history.replaceState({}, '', '/processes/edit?id=process-1');
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === 'PATCH') {
        const draft = JSON.parse(String(init.body)) as {
          stages: typeof process.stages;
        };
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ...process,
              stages: draft.stages.map((stage, position) => ({
                ...stage,
                position,
                status: stage.enabled ? 'not_started' : 'skipped',
                attempts: [],
              })),
            }),
            { status: 200 },
          ),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify(process), { status: 200 }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<ProcessForm mode="edit" />);

    const toggle = await screen.findByRole('switch', {
      name: 'Include Technical / experience',
    });
    fireEvent.click(toggle);

    await waitFor(
      () => {
        const patch = fetchMock.mock.calls.find(
          ([, init]) => init?.method === 'PATCH',
        );
        expect(patch).toBeDefined();
        expect(
          (
            JSON.parse(String(patch?.[1]?.body)) as {
              stages: Array<{ enabled: boolean }>;
            }
          ).stages[0].enabled,
        ).toBe(false);
      },
      { timeout: 2000 },
    );
  });

  it('renders stage history and repeat behavior on process details', async () => {
    window.history.replaceState({}, '', '/processes/details?id=process-1');
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(new Response(JSON.stringify(process), { status: 200 })),
      ),
    );

    render(<ProcessDetail />);

    expect(await screen.findByText('Backend role')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Edit process' })).toHaveAttribute(
      'href',
      '/processes/edit?id=process-1',
    );
    expect(screen.getByText('Attempt 1')).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Repeat interview' }),
    ).toBeVisible();
    expect(screen.getByText(/Feedback and interview scores/)).toBeVisible();
  });
});
