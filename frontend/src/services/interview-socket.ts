export interface SocketEvent<T = unknown> {
  protocol_version: string;
  event_id: string;
  attempt_id: string;
  timestamp: string;
  type: string;
  payload: T;
}

export class InterviewSocket {
  private socket?: WebSocket;

  connect(
    attemptId: string,
    onEvent: (event: SocketEvent) => void,
    onClose?: () => void,
  ): Promise<void> {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const configuredBase = import.meta.env.PUBLIC_WS_BASE_URL as
      string | undefined;
    const base = configuredBase ?? `${protocol}//${window.location.host}`;
    this.socket = new WebSocket(
      `${base}/api/v1/interviews/${encodeURIComponent(attemptId)}/ws`,
    );
    return new Promise((resolve, reject) => {
      if (!this.socket) return reject(new Error('WebSocket was not created'));
      this.socket.addEventListener('open', () => resolve(), { once: true });
      this.socket.addEventListener(
        'error',
        () => reject(new Error('Interview connection failed')),
        {
          once: true,
        },
      );
      this.socket.addEventListener('message', (message) => {
        onEvent(JSON.parse(String(message.data)) as SocketEvent);
      });
      if (onClose)
        this.socket.addEventListener('close', onClose, { once: true });
    });
  }

  send(type: string, payload: Record<string, unknown> = {}) {
    if (this.socket?.readyState !== WebSocket.OPEN) {
      throw new Error('Interview connection is not open');
    }
    this.socket.send(JSON.stringify({ type, payload }));
  }

  close() {
    this.socket?.close();
    this.socket = undefined;
  }
}
