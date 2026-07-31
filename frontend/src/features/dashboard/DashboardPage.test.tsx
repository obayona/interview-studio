import { render, screen, waitFor } from '@testing-library/react';
import axe from 'axe-core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardPage } from './DashboardPage';

const request = vi.fn();

vi.mock('../../services/dashboard-api', () => ({
  dashboardApi: { get: () => request() },
}));

const dashboard = {
  stats: {
    process_count: 1,
    active_process_count: 1,
    attempt_count: 2,
    completed_attempt_count: 2,
    evaluated_attempt_count: 2,
    average_score: 75,
    minimum_score: 64,
    maximum_score: 86,
  },
  score_trend: [
    {
      attempt_id: 'attempt-1',
      process_id: 'process-1',
      process_title: 'Platform role',
      score: 64,
      evaluated_at: '2026-07-29T10:00:00+00:00',
    },
    {
      attempt_id: 'attempt-2',
      process_id: 'process-1',
      process_title: 'Platform role',
      score: 86,
      evaluated_at: '2026-07-30T10:00:00+00:00',
    },
  ],
  recent_activity: [
    {
      attempt_id: 'attempt-2',
      process_id: 'process-1',
      process_title: 'Platform role',
      stage_type: 'technical',
      attempt_number: 2,
      status: 'completed',
      score: 86,
      occurred_at: '2026-07-30T10:00:00+00:00',
    },
  ],
  strengths: [{ label: 'Communication', count: 2 }],
  weaknesses: [{ label: 'Metrics', count: 2 }],
  onboarding: {
    settings_configured: true,
    profile_completed: false,
    process_created: true,
    interview_started: true,
  },
};

describe('DashboardPage', () => {
  beforeEach(() => request.mockReset());

  it('renders stored aggregates and only incomplete onboarding', async () => {
    request.mockResolvedValue(dashboard);
    const { container } = render(<DashboardPage />);

    expect(await screen.findByText('75')).toBeInTheDocument();
    expect(screen.getByText('64–86')).toBeInTheDocument();
    expect(screen.getByText('Platform role')).toBeInTheDocument();
    expect(screen.getByText('Communication')).toBeInTheDocument();
    expect(screen.getByText('Complete your profile')).toBeInTheDocument();
    expect(screen.queryByText('Upcoming sessions')).not.toBeInTheDocument();
    expect(screen.queryByText('Interview readiness')).not.toBeInTheDocument();
    expect(
      (
        await axe.run(container, {
          rules: { 'color-contrast': { enabled: false } },
        })
      ).violations,
    ).toEqual([]);
  });

  it('shows a retry state when loading fails', async () => {
    request
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValue(dashboard);
    render(<DashboardPage />);
    await waitFor(() =>
      expect(
        screen.getByText('Your dashboard could not be loaded.'),
      ).toBeInTheDocument(),
    );
  });
});
