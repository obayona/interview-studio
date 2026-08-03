import type { ApiErrorBody } from '../types/api';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = 'request_failed',
    readonly fieldErrors: Record<string, string[]> = {},
    readonly requestId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class ApiClient {
  private csrfToken = '';

  constructor(private readonly baseUrl = '') {}

  setCsrfToken(token: string) {
    this.csrfToken = token;
  }

  private async ensureCsrfToken() {
    if (this.csrfToken) return;
    const response = await fetch(`${this.baseUrl}/api/v1/auth/session`, {
      credentials: 'same-origin',
    });
    if (!response.ok) return;
    const session = (await response.json()) as { csrf_token?: string };
    this.csrfToken = session.csrf_token ?? '';
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      const method = (init.method ?? 'GET').toUpperCase();
      const needsCsrf =
        !['GET', 'HEAD', 'OPTIONS'].includes(method) &&
        path !== '/api/v1/auth/login';
      if (needsCsrf) await this.ensureCsrfToken();
      const isFormData = init.body instanceof FormData;
      response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        credentials: 'same-origin',
        headers: {
          ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
          ...(needsCsrf && this.csrfToken
            ? { 'X-CSRF-Token': this.csrfToken }
            : {}),
          ...init.headers,
        },
      });
    } catch {
      throw new ApiError(
        'The Interview Studio backend is unavailable.',
        0,
        'network_error',
      );
    }
    if (!response.ok) {
      let body: Partial<ApiErrorBody> = {};
      try {
        body = (await response.json()) as ApiErrorBody;
      } catch {
        // The normalized fallback below handles non-JSON upstream responses.
      }
      if (
        response.status === 401 &&
        path !== '/api/v1/auth/login' &&
        typeof window !== 'undefined' &&
        window.location.pathname !== '/login'
      ) {
        const next = `${window.location.pathname}${window.location.search}`;
        window.location.assign(`/login?next=${encodeURIComponent(next)}`);
      }
      throw new ApiError(
        body.message ?? `Request failed with status ${response.status}.`,
        response.status,
        body.code,
        body.field_errors,
        body.request_id,
      );
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }
}

export const apiClient = new ApiClient(
  import.meta.env.PUBLIC_API_BASE_URL ?? '',
);
