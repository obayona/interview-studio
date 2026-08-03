import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { forwardRef, useImperativeHandle } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { InterviewSimulator } from './InterviewSimulator';

const history = vi.fn();
const connect = vi.fn();
const send = vi.fn();
const close = vi.fn();
const navigate = vi.fn();
let emit: ((event: Record<string, unknown>) => void) | undefined;
const checkpoint = vi.hoisted(() => vi.fn());

vi.mock('../../services/interview-api', () => ({
  interviewApi: { history: (...args: unknown[]) => history(...args) },
}));

vi.mock('../../services/navigation', () => ({
  navigate: (...args: unknown[]) => navigate(...args),
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

vi.mock('./SystemDesignWhiteboard', () => ({
  SystemDesignWhiteboard: forwardRef(function WhiteboardMock(_, ref) {
    useImperativeHandle(ref, () => ({ checkpoint }));
    return <div aria-label="System design whiteboard" />;
  }),
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

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
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
    await waitFor(() =>
      expect(send).toHaveBeenCalledWith('user.text', {
        text: 'I build reliable systems.',
      }),
    );

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
      screen.getByRole('button', { name: 'Turn on voice answers' }),
    ).toHaveAttribute('title', 'Turn on voice answers');
    expect(screen.getByText('Voice input ready')).toBeVisible();
    expect(
      screen.getByText('Click the microphone to enable voice answers'),
    ).toBeVisible();

    act(() => {
      emit?.({
        type: 'interview.state',
        payload: { status: 'completed' },
      });
    });
    expect(navigate).toHaveBeenCalledWith(
      '/feedback?attempt=attempt-1&evaluate=1',
    );
    expect(
      screen.queryByRole('button', { name: 'End session' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Your answer')).not.toBeInTheDocument();
  });

  it('offers immediate handoff only during the voice countdown', async () => {
    class MediaRecorderMock extends EventTarget {
      mimeType = 'audio/webm';
      state: RecordingState = 'inactive';

      start() {
        this.state = 'recording';
      }

      stop() {
        const chunk = new Event('dataavailable');
        Object.defineProperty(chunk, 'data', {
          value: new Blob(['voice']),
        });
        this.dispatchEvent(chunk);
        this.state = 'inactive';
        this.dispatchEvent(new Event('stop'));
      }
    }

    vi.stubGlobal('MediaRecorder', MediaRecorderMock);
    vi.stubGlobal('AudioContext', undefined);
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }],
        }),
      },
    });
    render(<InterviewSimulator />);
    await waitFor(() => expect(connect).toHaveBeenCalled());
    act(() => {
      emit?.({
        type: 'session.ready',
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
      screen.queryByRole('button', { name: 'Finish answer now' }),
    ).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole('button', { name: 'Turn on voice answers' }),
    );
    const microphone = await screen.findByRole('button', {
      name: 'Hold to record a voice answer',
    });
    fireEvent.pointerDown(microphone);
    fireEvent.pointerUp(microphone);

    const finish = await screen.findByRole('button', {
      name: 'Finish answer now',
    });
    fireEvent.click(finish);
    await waitFor(() => expect(send).toHaveBeenCalledWith('user.turn.end'));
    expect(
      screen.queryByRole('button', { name: 'Finish answer now' }),
    ).not.toBeInTheDocument();
  });

  it('clears listening state and releases the microphone when voice is disabled', async () => {
    const stopTrack = vi.fn();
    class AudioContextMock {
      createAnalyser() {
        return {
          fftSize: 0,
          getByteTimeDomainData: vi.fn(),
        };
      }
      createMediaStreamSource() {
        return { connect: vi.fn() };
      }
      resume() {
        return Promise.resolve();
      }
      close() {
        return Promise.resolve();
      }
    }
    vi.stubGlobal('AudioContext', AudioContextMock);
    vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1);
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: stopTrack }],
        }),
      },
    });
    render(<InterviewSimulator />);
    await waitFor(() => expect(connect).toHaveBeenCalled());
    act(() => {
      emit?.({
        type: 'session.ready',
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

    fireEvent.click(
      screen.getByRole('button', { name: 'Turn on voice answers' }),
    );
    const disable = await screen.findByRole('button', {
      name: 'Turn off voice answers and discard pending speech',
    });
    fireEvent.click(disable);

    await waitFor(() => expect(stopTrack).toHaveBeenCalledOnce());
    expect(send).toHaveBeenCalledWith('user.turn.cancel');
    expect(
      screen.getByRole('button', { name: 'Turn on voice answers' }),
    ).toBeInTheDocument();
  });

  it('optimistically clears listening feedback when paused', async () => {
    render(<InterviewSimulator />);
    await waitFor(() => expect(connect).toHaveBeenCalled());
    act(() => {
      emit?.({
        type: 'session.ready',
        payload: {
          modes: { text_to_speech: false },
          capabilities: { speech_to_text: false },
        },
      });
      emit?.({ type: 'interview.state', payload: { status: 'listening' } });
      emit?.({
        type: 'transcript.partial',
        payload: { received_bytes: 2048 },
      });
    });
    expect(screen.getByText('Listening… 2 KiB')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }));

    expect(screen.queryByText('Listening… 2 KiB')).not.toBeInTheDocument();
    expect(screen.getByText('paused')).toBeVisible();
    expect(send).toHaveBeenCalledWith('session.pause');
  });

  it('submits a changed whiteboard checkpoint before a system-design answer', async () => {
    checkpoint.mockResolvedValue({ id: 'snapshot-1' });
    history.mockResolvedValue({
      attempt_id: 'attempt-1',
      status: 'ready',
      messages: [],
      context: {
        process_id: 'process-1',
        process_title: 'Architecture practice',
        company_name: '',
        target_role: 'Staff Engineer',
        stage_type: 'system_design',
        attempt_number: 1,
        company_info: '',
        job_listing: 'Design scalable systems.',
        difficulty: 'senior',
        interviewer_profile: 'staff_engineer',
        language: 'English',
        configured_topics: [],
        topics_covered: [],
        max_questions: 8,
        max_duration_minutes: 45,
      },
    });
    render(<InterviewSimulator />);
    await waitFor(() => expect(connect).toHaveBeenCalled());
    act(() => {
      emit?.({
        type: 'session.ready',
        payload: {
          modes: { text_to_speech: false },
          capabilities: { speech_to_text: false },
        },
      });
      emit?.({
        type: 'interview.state',
        payload: { status: 'ready_for_answer' },
      });
    });

    fireEvent.change(screen.getByLabelText('Your answer'), {
      target: { value: 'I would start with an API gateway.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send answer' }));

    await waitFor(() =>
      expect(send).toHaveBeenCalledWith('user.text', {
        text: 'I would start with an API gateway.',
      }),
    );
    const calls = send.mock.calls;
    expect(
      calls.findIndex(([type]) => type === 'canvas.snapshot'),
    ).toBeLessThan(calls.findIndex(([type]) => type === 'user.text'));
  });
});
