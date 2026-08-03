import { useCallback, useEffect, useRef, useState } from 'react';

const SILENCE_MS = 3000;
const MAX_SEGMENT_MS = 60_000;
const AUDIO_LEVEL_THRESHOLD = 0.025;

type VoiceCaptureOptions = {
  available: boolean;
  ready: boolean;
  onAudioStart: (mediaType: string) => void;
  onAudioChunk: (buffer: ArrayBuffer) => Promise<void>;
  onAudioEnd: () => void;
  onInterrupt: () => void;
  onError: (message: string) => void;
};

export function useVoiceCapture({
  available,
  ready,
  onAudioStart,
  onAudioChunk,
  onAudioEnd,
  onInterrupt,
  onError,
}: VoiceCaptureOptions) {
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const context = useRef<AudioContext | null>(null);
  const animationFrame = useRef<number | null>(null);
  const silenceStartedAt = useRef<number | null>(null);
  const segmentStartedAt = useRef<number | null>(null);
  const pendingChunks = useRef<Promise<void>[]>([]);
  const enabledRef = useRef(false);
  const readyRef = useRef(ready);
  const [enabled, setEnabled] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState<number>();
  const [manualFallback, setManualFallback] = useState(false);

  readyRef.current = ready;

  const stopSegment = useCallback(() => {
    silenceStartedAt.current = null;
    segmentStartedAt.current = null;
    setCountdown(undefined);
    if (recorder.current?.state === 'recording') recorder.current.stop();
  }, []);

  const startSegment = useCallback(() => {
    if (
      !stream.current ||
      !readyRef.current ||
      recorder.current?.state === 'recording'
    ) {
      return;
    }
    onInterrupt();
    const mediaRecorder = new MediaRecorder(stream.current);
    recorder.current = mediaRecorder;
    pendingChunks.current = [];
    onAudioStart(mediaRecorder.mimeType || 'audio/webm');
    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (!event.data.size) return;
      const pending = event.data
        .arrayBuffer()
        .then((buffer) => onAudioChunk(buffer));
      pendingChunks.current.push(pending);
    });
    mediaRecorder.addEventListener(
      'stop',
      () => {
        setRecording(false);
        recorder.current = null;
        void Promise.all(pendingChunks.current).then(onAudioEnd);
      },
      { once: true },
    );
    mediaRecorder.start(500);
    segmentStartedAt.current = performance.now();
    setRecording(true);
  }, [onAudioChunk, onAudioEnd, onAudioStart, onInterrupt]);

  const disable = useCallback(() => {
    enabledRef.current = false;
    setEnabled(false);
    setManualFallback(false);
    window.cancelAnimationFrame(animationFrame.current ?? 0);
    animationFrame.current = null;
    if (recorder.current?.state === 'recording') recorder.current.stop();
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    void context.current?.close();
    context.current = null;
    silenceStartedAt.current = null;
    segmentStartedAt.current = null;
    setCountdown(undefined);
  }, []);

  const enable = useCallback(async () => {
    if (!available || enabledRef.current) return;
    setRequesting(true);
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      enabledRef.current = true;
      setEnabled(true);

      const AudioContextConstructor = window.AudioContext;
      if (!AudioContextConstructor) {
        setManualFallback(true);
        return;
      }

      const audioContext = new AudioContextConstructor();
      context.current = audioContext;
      await audioContext.resume();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 1024;
      audioContext.createMediaStreamSource(stream.current).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);

      const detectSpeech = (timestamp: number) => {
        if (!enabledRef.current) return;
        analyser.getByteTimeDomainData(samples);
        let energy = 0;
        for (const sample of samples) {
          const normalized = (sample - 128) / 128;
          energy += normalized * normalized;
        }
        const speaking =
          Math.sqrt(energy / samples.length) > AUDIO_LEVEL_THRESHOLD;

        if (speaking) {
          silenceStartedAt.current = null;
          setCountdown(undefined);
          startSegment();
        } else if (recorder.current?.state === 'recording') {
          silenceStartedAt.current ??= timestamp;
          const elapsed = timestamp - silenceStartedAt.current;
          setCountdown(Math.max(1, Math.ceil((SILENCE_MS - elapsed) / 1000)));
          if (elapsed >= SILENCE_MS) stopSegment();
        }
        if (
          segmentStartedAt.current !== null &&
          timestamp - segmentStartedAt.current >= MAX_SEGMENT_MS
        ) {
          stopSegment();
        }
        animationFrame.current = window.requestAnimationFrame(detectSpeech);
      };
      animationFrame.current = window.requestAnimationFrame(detectSpeech);
    } catch {
      disable();
      onError('Microphone permission is required for voice answers.');
    } finally {
      setRequesting(false);
    }
  }, [available, disable, onError, startSegment, stopSegment]);

  const toggle = useCallback(() => {
    if (!enabled) void enable();
    else if (!manualFallback) disable();
  }, [disable, enable, enabled, manualFallback]);

  const startManual = useCallback(() => {
    if (manualFallback && enabled) startSegment();
  }, [enabled, manualFallback, startSegment]);

  const stopManual = useCallback(() => {
    if (manualFallback && recording) stopSegment();
  }, [manualFallback, recording, stopSegment]);

  useEffect(() => disable, [disable]);

  return {
    enabled,
    requesting,
    recording,
    countdown,
    manualFallback,
    toggle,
    startManual,
    stopManual,
    disable,
  };
}
