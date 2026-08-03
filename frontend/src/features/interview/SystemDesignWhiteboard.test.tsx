import React, { useEffect } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '../../components/ui/Toast';
import { SystemDesignWhiteboard } from './SystemDesignWhiteboard';

const getSession = vi.fn();
const saveScene = vi.fn();
const saveSnapshot = vi.fn();
let elements: unknown[] = [];

vi.mock('../../services/system-design-api', () => ({
  systemDesignApi: {
    get: (...args: unknown[]) => getSession(...args),
    save: (...args: unknown[]) => saveScene(...args),
    snapshot: (...args: unknown[]) => saveSnapshot(...args),
  },
}));

vi.mock('@excalidraw/excalidraw', () => ({
  Excalidraw: ({
    excalidrawAPI,
    onChange,
    viewModeEnabled,
  }: {
    excalidrawAPI: (api: Record<string, unknown>) => void;
    onChange: (elements: unknown[], appState: object, files: object) => void;
    viewModeEnabled: boolean;
  }) => {
    useEffect(() => {
      excalidrawAPI({
        getSceneElements: () => elements,
        getAppState: () => ({}),
        getFiles: () => ({}),
      });
    }, [excalidrawAPI]);
    return React.createElement(
      'button',
      {
        onClick: () => {
          elements = [{ id: 'api', type: 'rectangle' }];
          onChange(elements, {}, {});
        },
      },
      viewModeEnabled ? 'View-only canvas' : 'Draw shape',
    );
  },
  serializeAsJSON: (nextElements: unknown[]) =>
    JSON.stringify({ elements: nextElements, appState: {}, files: {} }),
  exportToBlob: () => Promise.resolve(new Blob(['png'], { type: 'image/png' })),
}));

describe('SystemDesignWhiteboard', () => {
  beforeEach(() => {
    elements = [];
    getSession.mockResolvedValue({
      attempt_id: 'attempt-1',
      scene: { elements: [], appState: {}, files: {} },
      scene_version: 0,
      snapshots: [],
    });
    saveScene.mockResolvedValue({
      attempt_id: 'attempt-1',
      scene: {
        elements: [{ id: 'api', type: 'rectangle' }],
        appState: {},
        files: {},
      },
      scene_version: 1,
      snapshots: [],
    });
    saveSnapshot.mockResolvedValue({
      id: 'snapshot-1',
      scene_version: 1,
      reason: 'explicit',
      created_at: new Date().toISOString(),
      image_url: '/snapshot.png',
    });
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: () => ({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('autosaves edits and creates an explicit PNG snapshot', async () => {
    render(
      <ToastProvider>
        <SystemDesignWhiteboard attemptId="attempt-1" />
      </ToastProvider>,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Draw shape' }));
    const snapshot = await screen.findByRole('button', {
      name: 'Save whiteboard snapshot',
    });
    expect(snapshot).toBeEnabled();
    fireEvent.click(snapshot);

    await waitFor(() => expect(saveScene).toHaveBeenCalledOnce());
    await waitFor(() => expect(saveSnapshot).toHaveBeenCalledOnce());
    expect(saveScene).toHaveBeenCalledWith(
      'attempt-1',
      expect.objectContaining({ elements: elements }),
      0,
    );
    expect(saveSnapshot.mock.calls[0][1]).toBe(1);
    expect(saveSnapshot.mock.calls[0][3]).toBe('explicit');
    expect(await screen.findByText('Whiteboard snapshot saved.')).toBeVisible();
  });
});
