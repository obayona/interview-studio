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
  onInterrupt: vi.fn(),
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

  it('automatically sends a detected utterance after three seconds of silence', async () => {
    const callbacks = options();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.enabled).toBe(true));

    signal = 140;
    act(() => animationCallback?.(0));
    expect(callbacks.onAudioStart).toHaveBeenCalledWith('audio/webm');
    expect(result.current.recording).toBe(true);

    signal = 128;
    act(() => animationCallback?.(100));
    expect(result.current.countdown).toBe(3);
    act(() => animationCallback?.(3100));

    await waitFor(() => expect(callbacks.onAudioEnd).toHaveBeenCalledOnce());
    expect(result.current.recording).toBe(false);
    expect(result.current.enabled).toBe(true);
  });

  it('cancels pending automatic send when speech resumes', async () => {
    const callbacks = options();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.enabled).toBe(true));
    signal = 140;
    act(() => animationCallback?.(0));
    signal = 128;
    act(() => animationCallback?.(100));
    signal = 140;
    act(() => animationCallback?.(2000));

    expect(result.current.countdown).toBeUndefined();
    expect(callbacks.onAudioEnd).not.toHaveBeenCalled();
  });

  it('uses press and release when browser audio analysis is unavailable', async () => {
    vi.stubGlobal('AudioContext', undefined);
    const callbacks = options();
    const { result } = renderHook(() => useVoiceCapture(callbacks));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.manualFallback).toBe(true));
    act(() => result.current.startManual());
    expect(result.current.recording).toBe(true);
    act(() => result.current.stopManual());

    await waitFor(() => expect(callbacks.onAudioEnd).toHaveBeenCalledOnce());
  });
});
