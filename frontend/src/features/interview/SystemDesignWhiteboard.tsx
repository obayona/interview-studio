import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import type {
  AppState,
  BinaryFiles,
  ExcalidrawImperativeAPI,
} from '@excalidraw/excalidraw/types';
import type { OrderedExcalidrawElement } from '@excalidraw/excalidraw/element/types';
import type { ImportedDataState } from '@excalidraw/excalidraw/data/types';
import '@excalidraw/excalidraw/index.css';
import { Button } from '../../components/ui/Button';
import { Icon } from '../../components/ui/Icon';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';
import { useAutosave } from '../../hooks/useAutosave';
import { ApiError } from '../../services/api-client';
import { systemDesignApi } from '../../services/system-design-api';
import type {
  SystemDesignSession,
  WhiteboardScene,
  WhiteboardSnapshot,
} from '../../types/system-design';
import './whiteboard.css';

type Draft = {
  scene: WhiteboardScene;
  expectedVersion: number;
};

const EMPTY_SCENE: WhiteboardScene = {
  elements: [],
  appState: {},
  files: {},
};

const SAVE_LABELS = {
  idle: 'Canvas ready',
  pending: 'Unsaved changes',
  saving: 'Saving canvas…',
  saved: 'Canvas saved',
  error: 'Save failed',
} as const;

export type SystemDesignWhiteboardHandle = {
  checkpoint: (
    reason?: 'explicit' | 'interview_end',
  ) => Promise<WhiteboardSnapshot | undefined>;
};

export const SystemDesignWhiteboard = forwardRef<
  SystemDesignWhiteboardHandle,
  { attemptId: string }
>(function SystemDesignWhiteboard({ attemptId }, ref) {
  const { showToast } = useToast();
  const api = useRef<ExcalidrawImperativeAPI | null>(null);
  const sceneRef = useRef<Draft>({ scene: EMPTY_SCENE, expectedVersion: 0 });
  const versionRef = useRef(0);
  const saveChain = useRef<Promise<void>>(Promise.resolve());
  const changedSinceSnapshot = useRef(false);
  const snapshottingRef = useRef(false);
  const latestSnapshot = useRef<WhiteboardSnapshot | undefined>(undefined);
  const loadRequest = useRef<Promise<Draft | undefined> | null>(null);
  const hydratingEditor = useRef(false);
  const [module, setModule] =
    useState<typeof import('@excalidraw/excalidraw')>();
  const [draft, setDraft] = useState<Draft>(sceneRef.current);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [snapshotting, setSnapshotting] = useState(false);
  const [editorKey, setEditorKey] = useState(0);

  const load = useCallback(() => {
    if (loadRequest.current) return loadRequest.current;
    setLoadError(false);
    const request = (async () => {
      try {
        const session = await systemDesignApi.get(attemptId);
        const value = {
          scene: session.scene,
          expectedVersion: session.scene_version,
        };
        sceneRef.current = value;
        versionRef.current = session.scene_version;
        changedSinceSnapshot.current = false;
        latestSnapshot.current = session.snapshots.at(-1);
        hydratingEditor.current = true;
        setDraft(value);
        setEditorKey((key) => key + 1);
        setLoaded(true);
        return value;
      } catch {
        setLoadError(true);
        return undefined;
      }
    })();
    loadRequest.current = request;
    void request.finally(() => {
      if (loadRequest.current === request) loadRequest.current = null;
    });
    return request;
  }, [attemptId]);

  const persistScene = useCallback(
    (value: Draft) => {
      const request = saveChain.current.then(async () => {
        const result = await systemDesignApi.save(
          attemptId,
          value.scene,
          versionRef.current,
        );
        versionRef.current = result.scene_version;
        return result;
      });
      saveChain.current = request.then(
        () => undefined,
        () => undefined,
      );
      return request;
    },
    [attemptId],
  );

  const autosave = useAutosave<Draft, SystemDesignSession>({
    value: draft,
    enabled: loaded,
    persist: persistScene,
    normalize: (result) => ({
      scene: result.scene,
      expectedVersion: result.scene_version,
    }),
    onSaved: (result, _normalized, _submitted, isCurrent) => {
      versionRef.current = result.scene_version;
      changedSinceSnapshot.current = true;
      setDraft((current) => {
        const next = {
          scene: isCurrent ? result.scene : current.scene,
          expectedVersion: result.scene_version,
        };
        sceneRef.current = next;
        return next;
      });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'stale_scene_version') {
        showToast(
          'The whiteboard changed elsewhere and was reloaded.',
          'error',
        );
        void load().then((value) => value && autosave.reset(value));
        return;
      }
      showToast('The whiteboard could not be saved.', 'error');
    },
  });
  const saveNow = autosave.saveNow;

  useEffect(() => {
    void import('@excalidraw/excalidraw').then(setModule);
    void load().then((value) => value && autosave.reset(value));
  }, [load]);

  useEffect(() => {
    const media = window.matchMedia('(width <= 760px)');
    const update = () => setMobile(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  const exportPng = useCallback(async () => {
    if (!module || !api.current || api.current.getSceneElements().length === 0)
      return undefined;
    return module.exportToBlob({
      elements: api.current.getSceneElements(),
      appState: {
        ...api.current.getAppState(),
        exportBackground: true,
      },
      files: api.current.getFiles(),
      mimeType: 'image/png',
    });
  }, [module]);

  const saveSnapshot = useCallback(
    async (
      reason: 'periodic' | 'explicit' | 'interview_end',
      announce = true,
    ) => {
      if (snapshottingRef.current || !changedSinceSnapshot.current) return;
      snapshottingRef.current = true;
      setSnapshotting(true);
      try {
        const saved = await saveNow(sceneRef.current);
        if (!saved) return;
        const image = await exportPng();
        if (!image || versionRef.current === 0) return;
        const snapshot = await systemDesignApi.snapshot(
          attemptId,
          versionRef.current,
          image,
          reason,
        );
        latestSnapshot.current = snapshot;
        changedSinceSnapshot.current = false;
        if (announce) showToast('Whiteboard snapshot saved.', 'success');
        return snapshot;
      } catch {
        if (announce)
          showToast('The whiteboard snapshot could not be saved.', 'error');
      } finally {
        snapshottingRef.current = false;
        setSnapshotting(false);
      }
    },
    [attemptId, exportPng, saveNow, showToast],
  );

  useImperativeHandle(
    ref,
    () => ({
      checkpoint: (reason = 'explicit') => saveSnapshot(reason, false),
    }),
    [saveSnapshot],
  );

  useEffect(() => {
    const timer = window.setInterval(
      () => void saveSnapshot('periodic', false),
      30_000,
    );
    return () => window.clearInterval(timer);
  }, [saveSnapshot]);

  const download = async () => {
    const image = await exportPng();
    if (!image) return;
    const url = URL.createObjectURL(image);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'system-design-whiteboard.png';
    link.click();
    URL.revokeObjectURL(url);
  };

  const onChange = (
    elements: readonly OrderedExcalidrawElement[],
    appState: AppState,
    files: BinaryFiles,
  ) => {
    if (!module || mobile) return;
    const scene = JSON.parse(
      module.serializeAsJSON(elements, appState, files, 'database'),
    ) as WhiteboardScene;
    if (hydratingEditor.current) {
      hydratingEditor.current = false;
      const persistedScene = sceneRef.current.scene;
      const contentIsUnchanged =
        JSON.stringify(scene.elements) ===
          JSON.stringify(persistedScene.elements) &&
        JSON.stringify(scene.files) === JSON.stringify(persistedScene.files);
      if (contentIsUnchanged) {
        const value = { scene, expectedVersion: versionRef.current };
        sceneRef.current = value;
        setDraft(value);
        autosave.reset(value);
        return;
      }
    }
    if (JSON.stringify(scene) === JSON.stringify(sceneRef.current.scene))
      return;
    const value = { scene, expectedVersion: versionRef.current };
    sceneRef.current = value;
    changedSinceSnapshot.current = true;
    setDraft(value);
    autosave.track(value);
  };

  if (loadError) {
    return (
      <div className="whiteboard whiteboard--state">
        <p>The whiteboard could not be loaded.</p>
        <Button onClick={() => void load()}>Retry</Button>
      </div>
    );
  }

  const Excalidraw = module?.Excalidraw;
  if (!loaded || !Excalidraw) {
    return (
      <div className="whiteboard whiteboard--state" role="status">
        <Spinner label="Loading whiteboard" />
      </div>
    );
  }

  return (
    <section className="whiteboard" aria-label="System design whiteboard">
      <div className="whiteboard__status">
        <span>
          {mobile ? 'View only on mobile' : SAVE_LABELS[autosave.status]}
        </span>
        <div className="whiteboard__actions">
          <Button
            className="ui-button--icon"
            aria-label="Save whiteboard snapshot"
            title="Save whiteboard snapshot"
            disabled={
              snapshotting ||
              !changedSinceSnapshot.current ||
              draft.scene.elements.length === 0
            }
            onClick={() => void saveSnapshot('explicit')}
          >
            <Icon
              name={snapshotting ? 'spinner' : 'save'}
              spin={snapshotting}
            />
          </Button>
          <Button
            className="ui-button--icon"
            aria-label="Export whiteboard as PNG"
            title="Export whiteboard as PNG"
            disabled={draft.scene.elements.length === 0}
            onClick={() => void download()}
          >
            <Icon name="download" />
          </Button>
        </div>
      </div>
      <div className="whiteboard__canvas">
        <Excalidraw
          key={editorKey}
          excalidrawAPI={(instance) => {
            api.current = instance;
          }}
          initialData={draft.scene as unknown as ImportedDataState}
          onChange={onChange}
          viewModeEnabled={mobile}
          zenModeEnabled
          gridModeEnabled
          name="System design"
        />
      </div>
    </section>
  );
});
