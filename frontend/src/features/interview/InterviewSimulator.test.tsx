import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InterviewSimulator } from './InterviewSimulator';

const history = vi.fn();
const connect = vi.fn();
const send = vi.fn();
const close = vi.fn();
let emit: ((event: Record<string, unknown>) => void) | undefined;

vi.mock('../../services/interview-api', () => ({
  interviewApi: { history: (...args: unknown[]) => history(...args) },
}));

vi.mock('../../services/interview-socket', () => ({
  InterviewSocket: class {
    connect(...args: unknown[]) {
      emit = args[1] as typeof emit;
      connect(...args);
      return Promise.resolve();
    }
    send(...args: unknown[]) {
      send(...args);
    }
    close() {
      close();
    }
  },
}));

describe('InterviewSimulator', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/interview?attempt=attempt-1');
    history.mockResolvedValue({
      attempt_id: 'attempt-1',
      status: 'ready',
      messages: [],
    });
  });

  it('hydrates, starts, streams messages, and supports live modes', async () => {
    render(<InterviewSimulator />);

    await waitFor(() => expect(connect).toHaveBeenCalled());
    expect(send).toHaveBeenCalledWith('session.start');

    act(() => {
      emit?.({
        type: 'session.ready',
        payload: {
          modes: { text_to_speech: true },
          capabilities: { speech_to_text: true },
        },
      });
      emit?.({
        type: 'interview.state',
        payload: { status: 'ready_for_answer' },
      });
      emit?.({
        type: 'assistant.text.delta',
        payload: { text: 'Tell me ' },
      });
    });

    expect(screen.getByLabelText('Interviewer is responding')).toBeVisible();

    act(() => {
      emit?.({
        type: 'assistant.text.completed',
        event_id: 'message-1',
        timestamp: new Date().toISOString(),
        payload: { text: 'Tell me about your experience.' },
      });
    });

    expect(
      await screen.findByText('Tell me about your experience.'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Hide transcript' }));
    expect(screen.queryByLabelText('Transcript')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Your answer')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Show transcript' }));
    expect(screen.getByLabelText('Transcript')).toBeVisible();
    expect(screen.getByLabelText('Your answer')).toBeVisible();

    fireEvent.change(screen.getByLabelText('Your answer'), {
      target: { value: 'I build reliable systems.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send answer' }));
    expect(send).toHaveBeenCalledWith('user.text', {
      text: 'I build reliable systems.',
    });

    fireEvent.click(screen.getByRole('button', { name: /Spoken replies/ }));
    expect(send).toHaveBeenCalledWith('mode.update', {
      text_to_speech: false,
    });

    act(() => {
      emit?.({
        type: 'mode.updated',
        payload: {
          modes: { text_to_speech: false },
          capabilities: { speech_to_text: true },
        },
      });
      emit?.({
        type: 'interview.state',
        payload: { status: 'ready_for_answer' },
      });
    });
    expect(
      screen.getByRole('button', { name: 'Start voice answer' }),
    ).toHaveAttribute('title', 'Start voice answer');
    expect(screen.getByText('Voice input ready')).toBeVisible();
    expect(
      screen.getByText('Click the microphone to start a voice answer'),
    ).toBeVisible();
    act(() => {
      emit?.({
        type: 'interview.state',
        payload: { status: 'listening' },
      });
    });
    expect(screen.getByText('Microphone live')).toBeVisible();
    expect(
      screen.getByText('Click the microphone again to stop and send'),
    ).toBeVisible();
    expect(
      screen.getByRole('button', {
        name: 'Stop recording and send voice answer',
      }),
    ).toBeVisible();

    act(() => {
      emit?.({
        type: 'interview.state',
        payload: { status: 'completed' },
      });
    });
    expect(
      screen.queryByRole('button', { name: 'End session' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Your answer')).not.toBeInTheDocument();
  });
});
