import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiClient, ApiError } from './api-client';

describe('ApiClient', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('normalizes structured backend errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: 'invalid_setting',
            message: 'The setting is invalid.',
            field_errors: { voice: ['Unsupported voice'] },
            request_id: 'request-1',
          }),
          { status: 422, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );

    const error = await new ApiClient()
      .request('/api/v1/settings')
      .catch((reason) => reason);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: 'invalid_setting',
      fieldErrors: { voice: ['Unsupported voice'] },
      requestId: 'request-1',
    });
  });

  it('returns a user-safe error when the backend is unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('connection refused')),
    );
    await expect(
      new ApiClient().request('/health/ready'),
    ).rejects.toMatchObject({
      code: 'network_error',
      status: 0,
    });
  });
});
