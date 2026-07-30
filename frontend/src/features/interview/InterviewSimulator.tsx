import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { Icon } from '../../components/ui/Icon';
import { ErrorState } from '../../components/ui/States';
import { ToastProvider, useToast } from '../../components/ui/Toast';
import interviewerImage from '../../images/interviewer.png';
import {
  interviewApi,
  type InterviewContext,
  type TranscriptMessage,
} from '../../services/interview-api';
import { profileApi } from '../../services/profile-api';
import {
  InterviewSocket,
  type SocketEvent,
} from '../../services/interview-socket';
import './interview.css';

type Modes = { speech_to_text: boolean; text_to_speech: boolean };
type Status =
  | 'connecting'
  | 'ready_for_answer'
  | 'listening'
  | 'transcribing'
  | 'paused'
  | 'completed';

function bytesToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 8192) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  }
  return window.btoa(binary);
}

function InterviewSimulatorContent() {
  const { showToast } = useToast();
  const socket = useRef(new InterviewSocket());
  const recorder = useRef<MediaRecorder | null>(null);
  const pendingChunks = useRef<Promise<void>[]>([]);
  const audioParts = useRef(new Map<string, string[]>());
  const playbackQueue = useRef<Blob[]>([]);
  const currentAudio = useRef<HTMLAudioElement | null>(null);
  const transcriptEnd = useRef<HTMLDivElement>(null);
  const reconnectTimer = useRef<number | undefined>(undefined);
  const intentionalClose = useRef(false);
  const [attemptId, setAttemptId] = useState<string>();
  const [processId, setProcessId] = useState<string>();
  const [candidate, setCandidate] = useState<{
    name: string;
    avatarUrl?: string;
  }>({ name: 'Candidate' });
  const [interviewContext, setInterviewContext] = useState<InterviewContext>();
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [chatVisible, setChatVisible] = useState(true);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [partialText, setPartialText] = useState('');
  const [modes, setModes] = useState<Modes>({
    speech_to_text: false,
    text_to_speech: false,
  });
  const [status, setStatus] = useState<Status>('connecting');
  const [error, setError] = useState<string>();
  const [connected, setConnected] = useState(false);

  const playNext = useCallback(() => {
    if (currentAudio.current || playbackQueue.current.length === 0) return;
    const blob = playbackQueue.current.shift();
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentAudio.current = audio;
    const finish = () => {
      URL.revokeObjectURL(url);
      currentAudio.current = null;
      playNext();
    };
    audio.addEventListener('ended', finish, { once: true });
    void audio.play().catch(() => {
      finish();
      showToast('Browser audio playback was blocked.', 'error');
    });
  }, [showToast]);

  const stopPlayback = useCallback(() => {
    currentAudio.current?.pause();
    currentAudio.current = null;
    playbackQueue.current = [];
    audioParts.current.clear();
  }, []);

  const queueAudio = useCallback(
    (audioId: string) => {
      const parts = audioParts.current.get(audioId);
      if (!parts?.length) return;
      const data = parts.map((part) => {
        const binary = window.atob(part);
        return Uint8Array.from(binary, (character) => character.charCodeAt(0));
      });
      playbackQueue.current.push(new Blob(data, { type: 'audio/mpeg' }));
      audioParts.current.delete(audioId);
      playNext();
    },
    [playNext],
  );

  const handleEvent = useCallback(
    (event: SocketEvent) => {
      const payload = event.payload as Record<string, unknown>;
      if (event.type === 'session.ready' || event.type === 'mode.updated') {
        setModes(payload.modes as Modes);
      } else if (event.type === 'assistant.text.delta') {
        setStreamingText((current) => current + String(payload.text ?? ''));
      } else if (event.type === 'assistant.text.completed') {
        const text = String(payload.text ?? '');
        setMessages((current) => [
          ...current,
          {
            id: event.event_id,
            sequence: current.length,
            role: 'assistant',
            text,
            created_at: event.timestamp,
          },
        ]);
        setStreamingText('');
      } else if (event.type === 'transcript.partial') {
        const received = Number(payload.received_bytes ?? 0);
        setPartialText(
          received
            ? `Listening… ${Math.ceil(received / 1024)} KiB`
            : 'Listening…',
        );
      } else if (event.type === 'transcript.final') {
        const text = String(payload.text ?? '');
        setPartialText('');
        setMessages((current) => [
          ...current,
          {
            id: event.event_id,
            sequence: current.length,
            role: 'user',
            text,
            created_at: event.timestamp,
          },
        ]);
      } else if (event.type === 'assistant.audio.chunk') {
        const audioId = String(payload.audio_id);
        const parts = audioParts.current.get(audioId) ?? [];
        parts.push(String(payload.audio));
        audioParts.current.set(audioId, parts);
      } else if (event.type === 'assistant.audio.completed') {
        queueAudio(String(payload.audio_id));
      } else if (event.type === 'assistant.audio.cancelled') {
        stopPlayback();
      } else if (event.type === 'interview.state') {
        setStatus(payload.status as Status);
      } else if (event.type === 'warning') {
        showToast(String(payload.message), 'error');
      } else if (event.type === 'error') {
        showToast(String(payload.message), 'error');
        setStatus('ready_for_answer');
      }
    },
    [queueAudio, showToast, stopPlayback],
  );

  const connect = useCallback(
    async (id: string) => {
      setStatus('connecting');
      try {
        const history = await interviewApi.history(id);
        setMessages(history.messages);
        setInterviewContext(history.context);
        await socket.current.connect(id, handleEvent, () => {
          setConnected(false);
          if (!intentionalClose.current) {
            reconnectTimer.current = window.setTimeout(
              () => void connect(id),
              1500,
            );
          }
        });
        setConnected(true);
        const completed = history.status === 'completed';
        socket.current.send(
          completed
            ? 'ping'
            : history.messages.length
              ? 'session.resume'
              : 'session.start',
        );
        if (completed) {
          setStatus('completed');
        } else if (history.messages.length) {
          setStatus('ready_for_answer');
        }
      } catch {
        setError('The interview could not be connected.');
      }
    },
    [handleEvent],
  );

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('attempt');
    if (!id) {
      setError('No interview attempt was selected.');
      return;
    }
    setAttemptId(id);
    setProcessId(
      new URLSearchParams(window.location.search).get('process') ?? undefined,
    );
    void connect(id);
    return () => {
      intentionalClose.current = true;
      window.clearTimeout(reconnectTimer.current);
      socket.current.close();
      stopPlayback();
      recorder.current?.stream.getTracks().forEach((track) => track.stop());
    };
  }, [connect, stopPlayback]);

  useEffect(() => {
    profileApi
      .get()
      .then((profile) =>
        setCandidate({
          name: profile.full_name || 'Candidate',
          avatarUrl: profile.avatar_url
            ? `${profile.avatar_url}?v=${encodeURIComponent(profile.updated_at)}`
            : undefined,
        }),
      )
      .catch(() => {
        // Candidate identity remains available through the fallback.
      });
  }, []);

  useEffect(() => {
    transcriptEnd.current?.scrollIntoView?.({ block: 'nearest' });
  }, [messages, partialText, streamingText]);

  const submit = () => {
    const text = draft.trim();
    if (!text || !connected || status !== 'ready_for_answer') return;
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        sequence: current.length,
        role: 'user',
        text,
        created_at: new Date().toISOString(),
      },
    ]);
    setDraft('');
    setStatus('connecting');
    socket.current.send('user.text', { text });
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stopPlayback();
      const mediaRecorder = new MediaRecorder(stream);
      recorder.current = mediaRecorder;
      pendingChunks.current = [];
      socket.current.send('user.audio.start', {
        media_type: mediaRecorder.mimeType || 'audio/webm',
      });
      mediaRecorder.addEventListener('dataavailable', (event) => {
        if (!event.data.size) return;
        const pending = event.data.arrayBuffer().then((buffer) => {
          socket.current.send('user.audio.chunk', {
            audio: bytesToBase64(buffer),
          });
        });
        pendingChunks.current.push(pending);
      });
      mediaRecorder.addEventListener(
        'stop',
        () => {
          void Promise.all(pendingChunks.current).then(() => {
            socket.current.send('user.audio.end');
            stream.getTracks().forEach((track) => track.stop());
          });
        },
        { once: true },
      );
      mediaRecorder.start(500);
      setStatus('listening');
    } catch {
      showToast('Microphone permission is required for push-to-talk.', 'error');
    }
  };

  const stopRecording = () => recorder.current?.stop();
  const updateMode = (key: keyof Modes) => {
    if (key === 'text_to_speech' && modes.text_to_speech) stopPlayback();
    socket.current.send('mode.update', { [key]: !modes[key] });
  };
  const interviewerIsStreaming = Boolean(streamingText);
  const openNavigation = () => {
    const shell = document.querySelector<HTMLElement>('.app-shell');
    const sidebar = document.querySelector<HTMLElement>('.app-shell__sidebar');
    if (shell) shell.dataset.menuOpen = 'true';
    if (sidebar) {
      sidebar.inert = false;
      sidebar.setAttribute('aria-hidden', 'false');
    }
  };

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={attemptId ? () => void connect(attemptId) : undefined}
      />
    );
  }

  return (
    <section className="interview" aria-label="Interview simulator">
      <header className="interview__status">
        <Button
          className="interview__menu ui-button--icon"
          aria-label="Open navigation"
          title="Open navigation"
          onClick={openNavigation}
        >
          <Icon name="bars" />
        </Button>
        <a
          className="interview__back ui-button ui-button--icon"
          href={
            processId
              ? `/processes/details?id=${encodeURIComponent(processId)}`
              : '/processes'
          }
          aria-label="Back to process"
          title="Back to process"
        >
          <Icon name="arrowLeft" />
        </a>
        <span
          className={`interview__status-dot ${connected ? 'is-connected' : ''}`}
        />
        <strong>{connected ? 'Live interview' : 'Reconnecting…'}</strong>
        <span>{status.replaceAll('_', ' ')}</span>
        <span
          className="interview__candidate"
          title={candidate.name}
          aria-label={candidate.name}
        >
          {candidate.avatarUrl ? (
            <img
              src={candidate.avatarUrl}
              alt=""
              onError={() =>
                setCandidate((current) => ({
                  ...current,
                  avatarUrl: undefined,
                }))
              }
            />
          ) : (
            <Icon name="user" />
          )}
        </span>
      </header>

      <div
        className={`interview__meeting ${chatVisible ? 'is-chat-visible' : ''}`}
      >
        <section className="interview__stage" aria-label="Interviewer">
          <div
            className={`interview__interviewer ${
              interviewerIsStreaming ? 'is-streaming' : ''
            }`}
            aria-label={
              interviewerIsStreaming
                ? 'Interviewer is responding'
                : 'Interviewer'
            }
          >
            <div className="interview__interviewer-portrait">
              <img src={interviewerImage.src} alt="AI interviewer" />
            </div>
            <strong>Interviewer</strong>
            <span>{interviewerIsStreaming ? 'Responding…' : 'Ready'}</span>
          </div>
        </section>

        {chatVisible && (
          <section className="interview__chat" aria-label="Transcript">
            <div className="interview__conversation" aria-live="polite">
              {messages.length === 0 && !streamingText && (
                <div className="interview__welcome">
                  <h2>Your interviewer is getting ready</h2>
                  <p>The first question will appear here.</p>
                </div>
              )}
              {messages.map((message) => (
                <article
                  className={`interview__message interview__message--${message.role}`}
                  key={message.id}
                >
                  <span>
                    {message.role === 'assistant' ? 'Interviewer' : 'You'}
                  </span>
                  <div className="interview__bubble">
                    <p>{message.text}</p>
                  </div>
                </article>
              ))}
              {(streamingText || partialText) && (
                <article className="interview__message interview__message--assistant">
                  <span>{partialText ? 'You' : 'Interviewer'}</span>
                  <div className="interview__bubble">
                    <p>{partialText || streamingText}</p>
                  </div>
                </article>
              )}
              <div ref={transcriptEnd} />
            </div>
            {status !== 'completed' && (
              <div className="interview__answer">
                <label className="sr-only" htmlFor="interview-answer">
                  Your answer
                </label>
                <textarea
                  id="interview-answer"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      submit();
                    }
                  }}
                  placeholder="Type your answer…"
                  disabled={!connected || status !== 'ready_for_answer'}
                />
                <Button
                  className="ui-button--icon"
                  variant="primary"
                  aria-label="Send answer"
                  title="Send answer"
                  disabled={!draft.trim() || status !== 'ready_for_answer'}
                  onClick={submit}
                >
                  <Icon name="send" />
                </Button>
              </div>
            )}
          </section>
        )}
      </div>

      <footer className="interview__controls">
        <div className="interview__identity">
          <strong>
            {interviewContext?.process_title || 'Practice interview'}
          </strong>
          <span>
            Attempt{' '}
            {interviewContext?.attempt_number
              ? `#${interviewContext.attempt_number}`
              : ''}
          </span>
        </div>
        <div className="interview__button-bar interview__button-bar--session">
          {status !== 'completed' && (
            <>
              <Button
                className={`interview__control ui-button--icon ${
                  modes.speech_to_text ? 'is-active' : ''
                }`}
                aria-pressed={modes.speech_to_text}
                aria-label="Voice answers"
                title="Voice answers"
                onClick={() => updateMode('speech_to_text')}
              >
                <Icon
                  name={modes.speech_to_text ? 'microphone' : 'microphoneOff'}
                />
              </Button>
              <Button
                className={`interview__control ui-button--icon ${
                  modes.text_to_speech ? 'is-active' : ''
                }`}
                aria-pressed={modes.text_to_speech}
                aria-label="Spoken replies"
                title="Spoken replies"
                onClick={() => updateMode('text_to_speech')}
              >
                <Icon name={modes.text_to_speech ? 'volume' : 'volumeOff'} />
              </Button>
              {modes.speech_to_text && (
                <Button
                  className={`interview__control interview__talk ui-button--icon ${
                    status === 'listening' ? 'is-listening is-active' : ''
                  }`}
                  aria-label={
                    status === 'listening' ? 'Stop and send' : 'Push to talk'
                  }
                  title={
                    status === 'listening' ? 'Stop and send' : 'Push to talk'
                  }
                  disabled={
                    !connected ||
                    !['ready_for_answer', 'listening'].includes(status)
                  }
                  onClick={
                    status === 'listening'
                      ? stopRecording
                      : () => void startRecording()
                  }
                >
                  <Icon
                    name={
                      status === 'listening' ? 'microphoneOff' : 'microphone'
                    }
                  />
                </Button>
              )}
              <Button
                className={`interview__control ui-button--icon ${
                  status === 'paused' ? 'is-active' : ''
                }`}
                aria-pressed={status === 'paused'}
                aria-label={status === 'paused' ? 'Resume' : 'Pause'}
                title={status === 'paused' ? 'Resume' : 'Pause'}
                onClick={() => {
                  const next =
                    status === 'paused' ? 'session.resume' : 'session.pause';
                  socket.current.send(next);
                }}
              >
                <Icon name={status === 'paused' ? 'resume' : 'pause'} />
              </Button>
              <Button
                className="interview__control ui-button--icon"
                variant="danger"
                aria-label="End session"
                title="End session"
                onClick={() => socket.current.send('session.end')}
              >
                <Icon name="hangup" />
              </Button>
            </>
          )}
        </div>
        <div className="interview__button-bar interview__button-bar--context">
          <Button
            className={`interview__control ui-button--icon ${
              chatVisible ? 'is-active' : ''
            }`}
            aria-pressed={chatVisible}
            aria-label={chatVisible ? 'Hide transcript' : 'Show transcript'}
            title={chatVisible ? 'Hide transcript' : 'Show transcript'}
            onClick={() => setChatVisible((visible) => !visible)}
          >
            <Icon name="interview" />
          </Button>
          <Button
            className={`interview__control ui-button--icon ${
              detailsOpen ? 'is-active' : ''
            }`}
            aria-pressed={detailsOpen}
            aria-label="Interview details"
            title="Interview details"
            onClick={() => setDetailsOpen(true)}
          >
            <Icon name="info" />
          </Button>
        </div>
      </footer>

      <Dialog
        className="interview__details-dialog"
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
      >
        <div className="ui-dialog__content interview__details">
          <div className="interview__details-heading">
            <div>
              <p className="interview__details-eyebrow">Interview context</p>
              <h2>{interviewContext?.process_title || 'Practice interview'}</h2>
            </div>
            <Button
              className="ui-button--icon"
              aria-label="Close interview details"
              title="Close interview details"
              onClick={() => setDetailsOpen(false)}
            >
              <Icon name="close" />
            </Button>
          </div>
          {interviewContext && (
            <>
              <dl className="interview__details-grid">
                <div>
                  <dt>Company</dt>
                  <dd>{interviewContext.company_name || 'Not specified'}</dd>
                </div>
                <div>
                  <dt>Target role</dt>
                  <dd>{interviewContext.target_role || 'Not specified'}</dd>
                </div>
                <div>
                  <dt>Stage</dt>
                  <dd>{interviewContext.stage_type.replaceAll('_', ' ')}</dd>
                </div>
                <div>
                  <dt>Difficulty</dt>
                  <dd>{interviewContext.difficulty}</dd>
                </div>
                <div>
                  <dt>Interviewer</dt>
                  <dd>
                    {interviewContext.interviewer_profile.replaceAll('_', ' ')}
                  </dd>
                </div>
                <div>
                  <dt>Limits</dt>
                  <dd>
                    {interviewContext.max_questions} questions ·{' '}
                    {interviewContext.max_duration_minutes} minutes
                  </dd>
                </div>
              </dl>
              {interviewContext.topics_covered.length > 0 && (
                <section>
                  <h3>Topics covered</h3>
                  <ul className="interview__topic-list">
                    {interviewContext.topics_covered.map((topic) => (
                      <li key={topic}>{topic}</li>
                    ))}
                  </ul>
                </section>
              )}
              {interviewContext.configured_topics.length > 0 && (
                <section>
                  <h3>Planned topics</h3>
                  <p>{interviewContext.configured_topics.join(', ')}</p>
                </section>
              )}
              {interviewContext.company_info && (
                <section>
                  <h3>Company information</h3>
                  <p>{interviewContext.company_info}</p>
                </section>
              )}
              {interviewContext.job_listing && (
                <section>
                  <h3>Role information</h3>
                  <p>{interviewContext.job_listing}</p>
                </section>
              )}
            </>
          )}
        </div>
      </Dialog>
    </section>
  );
}

export function InterviewSimulator() {
  return (
    <ToastProvider>
      <InterviewSimulatorContent />
    </ToastProvider>
  );
}
