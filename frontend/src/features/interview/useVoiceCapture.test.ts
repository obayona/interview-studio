import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useVoiceCapture } from './useVoiceCapture';

let animationCallback: FrameRequestCallback | undefined;
let signal = 128;

class MockMediaRecorder extends EventTarget {
  mimeType = 'audio/webm';
  state: RecordingState = 'inactive';

  start() {
    this.state = 'recording';
  }

  stop() {
    this.state = 'inactive';
    this.dispatchEvent(new Event('stop'));
  }
}

class MockAudioContext {
  createAnalyser() {
    return {
      fftSize: 0,
      getByteTimeDomainData: (samples: Uint8Array) => samples.fill(signal),
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

const options = () => ({
  available: true,
  ready: true,
  onAudioStart: vi.fn(),
  onAudioChunk: vi.fn(),
  onAudioEnd: vi.fn(),
  onTurnEnd: vi.fn(),
  onTurnCancel: vi.fn(),
  onError: vi.fn(),
});

describe('useVoiceCapture', () => {
  beforeEach(() => {
    signal = 128;
    animationCallback = undefined;
    vi.stubGlobal('MediaRecorder', MockMediaRecorder);
    vi.stubGlobal('AudioContext', MockAudioContext);
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      animationCallback = callback;
      return 1;
    });
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }],
        }),
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('captures after three seconds of silence and hands off five seconds later', async () => {
    const callbacks = options();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.enabled).toBe(true));

    signal = 140;
    act(() => animationCallback?.(0));
    expect(result.current.recording).toBe(true);

    signal = 128;
    act(() => animationCallback?.(100));
    act(() => animationCallback?.(3100));
    await waitFor(() => expect(callbacks.onAudioEnd).toHaveBeenCalledOnce());
    expect(result.current.countdown).toBe(5);
    expect(callbacks.onTurnEnd).not.toHaveBeenCalled();

    act(() => animationCallback?.(8101));
    expect(callbacks.onTurnEnd).toHaveBeenCalledOnce();
    expect(result.current.hasPendingTurn).toBe(false);
  });

  it('cancels handoff when speech resumes', async () => {
    const callbacks = options();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.enabled).toBe(true));
    signal = 140;
    act(() => animationCallback?.(0));
    signal = 128;
    act(() => animationCallback?.(100));
    act(() => animationCallback?.(3100));
    await waitFor(() => expect(callbacks.onAudioEnd).toHaveBeenCalledOnce());

    signal = 140;
    act(() => animationCallback?.(5000));
    expect(result.current.countdown).toBeUndefined();
    expect(result.current.recording).toBe(true);
    expect(callbacks.onTurnEnd).not.toHaveBeenCalled();
  });

  it('rotates a long segment without handing off the turn', async () => {
    const callbacks = options();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.enabled).toBe(true));
    signal = 140;
    act(() => animationCallback?.(0));
    act(() => animationCallback?.(45_001));
    await waitFor(() => expect(callbacks.onAudioEnd).toHaveBeenCalledOnce());
    act(() => animationCallback?.(45_100));

    expect(callbacks.onAudioStart).toHaveBeenCalledTimes(2);
    expect(callbacks.onTurnEnd).not.toHaveBeenCalled();
    expect(result.current.countdown).toBeUndefined();
  });

  it('does not capture while the interviewer owns the turn', async () => {
    const callbacks = options();
    const { result, rerender } = renderHook(
      ({ ready }) => useVoiceCapture({ ...callbacks, ready }),
      { initialProps: { ready: false } },
    );

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.enabled).toBe(true));
    signal = 140;
    act(() => animationCallback?.(0));
    expect(callbacks.onAudioStart).not.toHaveBeenCalled();

    rerender({ ready: true });
    act(() => animationCallback?.(100));
    expect(callbacks.onAudioStart).toHaveBeenCalledOnce();
  });

  it('uses press and release as a segment fallback', async () => {
    vi.stubGlobal('AudioContext', undefined);
    const callbacks = options();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.manualFallback).toBe(true));
    act(() => result.current.startManual());
    act(() => result.current.stopManual());

    await waitFor(() => expect(callbacks.onAudioEnd).toHaveBeenCalledOnce());
    expect(result.current.countdown).toBe(5);
    expect(callbacks.onTurnEnd).not.toHaveBeenCalled();
  });

  it('discards a pending segment before running a pause action', async () => {
    const callbacks = options();
    const afterCancel = vi.fn();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.enabled).toBe(true));
    signal = 140;
    act(() => animationCallback?.(0));
    act(() => result.current.cancelTurn(afterCancel));

    await waitFor(() => expect(callbacks.onTurnCancel).toHaveBeenCalledOnce());
    expect(callbacks.onAudioEnd).not.toHaveBeenCalled();
    expect(afterCancel).toHaveBeenCalledOnce();
    expect(result.current.hasPendingTurn).toBe(false);
  });
});
