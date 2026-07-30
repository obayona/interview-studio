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
  constructor(private readonly baseUrl = '') {}

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      const isFormData = init.body instanceof FormData;
      response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers: {
          ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
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
