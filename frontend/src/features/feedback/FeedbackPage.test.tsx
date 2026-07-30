import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../services/api-client';
import { FeedbackPage } from './FeedbackPage';

const getAttempt = vi.fn();
const evaluate = vi.fn();
const getProcess = vi.fn();
const history = vi.fn();

vi.mock('../../services/report-api', () => ({
  reportApi: {
    getAttempt: (...args: unknown[]) => getAttempt(...args),
    evaluate: (...args: unknown[]) => evaluate(...args),
    getProcess: (...args: unknown[]) => getProcess(...args),
  },
}));

vi.mock('../../services/interview-api', () => ({
  interviewApi: { history: (...args: unknown[]) => history(...args) },
}));

const report = {
  schema_version: '1.0',
  evaluation_version: 1,
  overall_score: 82,
  summary: 'Strong structure with room for more measurable detail.',
  competencies: {
    communication: 85,
    technical_knowledge: 80,
    problem_solving: 82,
    confidence: 78,
    answer_relevance: 86,
  },
  strengths: [
    {
      title: 'Clear structure',
      detail: 'The answer was easy to follow.',
      evidence: [{ message_id: 'user-1', explanation: 'Logical sequence.' }],
    },
  ],
  improvements: [
    {
      title: 'Add metrics',
      detail: 'State the measurable outcome.',
      evidence: [{ message_id: 'user-1', explanation: 'No result given.' }],
    },
  ],
  strong_topics: ['APIs'],
  weak_topics: ['Metrics'],
  answer_observations: [
    {
      message_id: 'user-1',
      score: 82,
      observation: 'Relevant answer.',
      advice: 'Add a measurable result.',
    },
  ],
  advice: ['Practice concise STAR answers.'],
  study_plan: [
    {
      priority: 1,
      topic: 'Impact statements',
      action: 'Rewrite two answers with metrics.',
    },
  ],
};

describe('FeedbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState(
      {},
      '',
      '/feedback?attempt=attempt-1&process=process-1&evaluate=1',
    );
    getAttempt.mockRejectedValue(
      new ApiError('Not evaluated.', 404, 'report_not_found'),
    );
    evaluate.mockResolvedValue(report);
    history.mockResolvedValue({
      messages: [
        {
          id: 'user-1',
          sequence: 0,
          role: 'user',
          text: 'I designed a reliable API.',
          created_at: '2026-07-30T00:00:00Z',
        },
      ],
    });
  });

  it('evaluates a missing report and renders evidence-linked feedback', async () => {
    let resolveEvaluation: ((value: typeof report) => void) | undefined;
    evaluate.mockImplementation(
      () =>
        new Promise<typeof report>((resolve) => {
          resolveEvaluation = resolve;
        }),
    );
    render(<FeedbackPage />);

    expect(await screen.findByText('Evaluating your interview…')).toBeVisible();
    await waitFor(() => expect(evaluate).toHaveBeenCalledWith('attempt-1'));
    await act(async () => resolveEvaluation?.(report));
    expect(await screen.findByText('82')).toBeVisible();
    expect(screen.getByText('Clear structure')).toBeVisible();
    expect(screen.getByText('I designed a reliable API.')).toBeVisible();
    expect(screen.getByText('Relevant answer.')).toBeVisible();
  });

  it('shows a retry action when evaluation fails', async () => {
    evaluate.mockRejectedValue(new ApiError('Provider failed.', 502));
    render(<FeedbackPage />);

    expect(await screen.findByText('Provider failed.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeVisible();
  });
});
