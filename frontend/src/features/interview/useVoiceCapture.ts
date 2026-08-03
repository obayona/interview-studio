import { useCallback, useEffect, useRef, useState } from 'react';

const SEGMENT_SILENCE_MS = 3000;
const HANDOFF_COUNTDOWN_MS = 5000;
const MAX_SEGMENT_MS = 45_000;
const AUDIO_LEVEL_THRESHOLD = 0.025;

type VoiceCaptureOptions = {
  available: boolean;
  ready: boolean;
  onAudioStart: (mediaType: string) => void;
  onAudioChunk: (buffer: ArrayBuffer) => Promise<void>;
  onAudioEnd: () => void;
  onTurnEnd: () => void;
  onTurnCancel: () => void;
  onError: (message: string) => void;
};

export function useVoiceCapture({
  available,
  ready,
  onAudioStart,
  onAudioChunk,
  onAudioEnd,
  onTurnEnd,
  onTurnCancel,
  onError,
}: VoiceCaptureOptions) {
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const context = useRef<AudioContext | null>(null);
  const animationFrame = useRef<number | null>(null);
  const silenceStartedAt = useRef<number | null>(null);
  const handoffStartedAt = useRef<number | null>(null);
  const segmentStartedAt = useRef<number | null>(null);
  const pendingChunks = useRef<Promise<void>[]>([]);
  const segmentEnding = useRef(false);
  const turnEndRequested = useRef(false);
  const discardSegment = useRef(false);
  const notifyTurnCancel = useRef(false);
  const afterCancel = useRef<(() => void) | undefined>(undefined);
  const enabledRef = useRef(false);
  const readyRef = useRef(ready);
  const [enabled, setEnabled] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState<number>();
  const [manualFallback, setManualFallback] = useState(false);
  const [hasPendingTurn, setHasPendingTurn] = useState(false);

  readyRef.current = ready;

  const sendTurn = useCallback(() => {
    if (segmentEnding.current) {
      turnEndRequested.current = true;
      return;
    }
    turnEndRequested.current = false;
    handoffStartedAt.current = null;
    setCountdown(undefined);
    setHasPendingTurn(false);
    onTurnEnd();
  }, [onTurnEnd]);

  const stopSegment = useCallback(
    (startHandoff: boolean, stoppedAt = performance.now()) => {
      silenceStartedAt.current = null;
      segmentStartedAt.current = null;
      if (startHandoff) {
        handoffStartedAt.current = stoppedAt;
        setCountdown(Math.ceil(HANDOFF_COUNTDOWN_MS / 1000));
      }
      if (recorder.current?.state === 'recording') {
        segmentEnding.current = true;
        recorder.current.stop();
      }
    },
    [],
  );

  const startSegment = useCallback(
    (startedAt = performance.now()) => {
      if (
        !stream.current ||
        !readyRef.current ||
        segmentEnding.current ||
        recorder.current?.state === 'recording'
      ) {
        return;
      }
      handoffStartedAt.current = null;
      turnEndRequested.current = false;
      setCountdown(undefined);
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
          void Promise.all(pendingChunks.current).then(() => {
            if (discardSegment.current) {
              segmentEnding.current = false;
              discardSegment.current = false;
              if (notifyTurnCancel.current) onTurnCancel();
              notifyTurnCancel.current = false;
              afterCancel.current?.();
              afterCancel.current = undefined;
              return;
            }
            onAudioEnd();
            segmentEnding.current = false;
            if (turnEndRequested.current) sendTurn();
          });
        },
        { once: true },
      );
      mediaRecorder.start(500);
      segmentStartedAt.current = startedAt;
      setRecording(true);
      setHasPendingTurn(true);
    },
    [onAudioChunk, onAudioEnd, onAudioStart, onTurnCancel, sendTurn],
  );

  const disable = useCallback(() => {
    enabledRef.current = false;
    setEnabled(false);
    setManualFallback(false);
    window.cancelAnimationFrame(animationFrame.current ?? 0);
    animationFrame.current = null;
    if (recorder.current?.state === 'recording') {
      discardSegment.current = true;
      notifyTurnCancel.current = false;
      recorder.current.stop();
    }
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    void context.current?.close();
    context.current = null;
    silenceStartedAt.current = null;
    handoffStartedAt.current = null;
    segmentStartedAt.current = null;
    turnEndRequested.current = false;
    setCountdown(undefined);
    setHasPendingTurn(false);
  }, []);

  const cancelTurn = useCallback(
    (after?: () => void) => {
      silenceStartedAt.current = null;
      handoffStartedAt.current = null;
      segmentStartedAt.current = null;
      turnEndRequested.current = false;
      setCountdown(undefined);
      setHasPendingTurn(false);
      if (recorder.current?.state === 'recording' || segmentEnding.current) {
        discardSegment.current = true;
        notifyTurnCancel.current = true;
        afterCancel.current = after;
        if (recorder.current?.state === 'recording') recorder.current.stop();
        return;
      }
      onTurnCancel();
      after?.();
    },
    [onTurnCancel],
  );

  const enable = useCallback(async () => {
    if (!available || enabledRef.current) return;
    setRequesting(true);
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
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

        if (speaking && readyRef.current) {
          silenceStartedAt.current = null;
          handoffStartedAt.current = null;
          setCountdown(undefined);
          startSegment(timestamp);
        } else if (recorder.current?.state === 'recording') {
          silenceStartedAt.current ??= timestamp;
          if (timestamp - silenceStartedAt.current >= SEGMENT_SILENCE_MS) {
            stopSegment(true, timestamp);
          }
        }

        if (
          segmentStartedAt.current !== null &&
          timestamp - segmentStartedAt.current >= MAX_SEGMENT_MS
        ) {
          stopSegment(false, timestamp);
        }

        if (handoffStartedAt.current !== null) {
          const remaining =
            HANDOFF_COUNTDOWN_MS - (timestamp - handoffStartedAt.current);
          setCountdown(Math.max(1, Math.ceil(remaining / 1000)));
          if (remaining <= 0) sendTurn();
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
  }, [available, disable, onError, sendTurn, startSegment, stopSegment]);

  const toggle = useCallback(() => {
    if (!enabled) void enable();
    else if (!manualFallback) disable();
  }, [disable, enable, enabled, manualFallback]);

  const startManual = useCallback(() => {
    if (manualFallback && enabled) startSegment();
  }, [enabled, manualFallback, startSegment]);

  const stopManual = useCallback(() => {
    if (manualFallback && recording) stopSegment(true);
  }, [manualFallback, recording, stopSegment]);

  useEffect(() => disable, [disable]);

  return {
    enabled,
    requesting,
    recording,
    countdown,
    manualFallback,
    hasPendingTurn,
    toggle,
    startManual,
    stopManual,
    finishTurn: sendTurn,
    cancelTurn,
    disable,
  };
}
