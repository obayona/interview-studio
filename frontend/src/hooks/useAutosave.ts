import { useCallback, useEffect, useRef, useState } from 'react';

export type SaveStatus = 'idle' | 'pending' | 'saving' | 'saved' | 'error';

interface AutosaveOptions<Value, Result> {
  value: Value;
  enabled: boolean;
  persist: (value: Value) => Promise<Result>;
  normalize: (result: Result) => Value;
  onSaved?: (
    result: Result,
    normalized: Value,
    submitted: Value,
    isCurrent: boolean,
    announced: boolean,
  ) => void;
  onError: (error: unknown) => void;
  onAlreadySaved?: () => void;
  delay?: number;
}

export function useAutosave<Value, Result>(
  options: AutosaveOptions<Value, Result>,
) {
  const [status, setStatus] = useState<SaveStatus>('idle');
  const optionsRef = useRef(options);
  const valueRef = useRef(options.value);
  const lastSaved = useRef(JSON.stringify(options.value));
  const savingSnapshot = useRef<string | undefined>(undefined);
  const requestSequence = useRef(0);
  optionsRef.current = options;
  valueRef.current = options.value;

  const track = useCallback((value: Value) => {
    valueRef.current = value;
  }, []);

  const reset = useCallback((value: Value) => {
    valueRef.current = value;
    lastSaved.current = JSON.stringify(value);
    setStatus('idle');
  }, []);

  const saveNow = useCallback(
    async (value = valueRef.current, announced = false) => {
      const snapshot = JSON.stringify(value);
      if (snapshot === lastSaved.current) {
        setStatus('saved');
        if (announced) optionsRef.current.onAlreadySaved?.();
        return true;
      }
      if (snapshot === savingSnapshot.current) return false;
      const sequence = ++requestSequence.current;
      savingSnapshot.current = snapshot;
      setStatus('saving');
      try {
        const result = await optionsRef.current.persist(value);
        if (sequence !== requestSequence.current) return false;
        const normalized = optionsRef.current.normalize(result);
        lastSaved.current = JSON.stringify(normalized);
        const isCurrent = JSON.stringify(valueRef.current) === snapshot;
        setStatus(isCurrent ? 'saved' : 'pending');
        optionsRef.current.onSaved?.(
          result,
          normalized,
          value,
          isCurrent,
          announced,
        );
        return true;
      } catch (error) {
        if (sequence !== requestSequence.current) return false;
        setStatus('error');
        optionsRef.current.onError(error);
        return false;
      } finally {
        if (savingSnapshot.current === snapshot) {
          savingSnapshot.current = undefined;
        }
      }
    },
    [],
  );

  useEffect(() => {
    if (!options.enabled || JSON.stringify(options.value) === lastSaved.current)
      return;
    setStatus('pending');
    const timer = window.setTimeout(
      () => void saveNow(options.value),
      options.delay ?? 700,
    );
    return () => window.clearTimeout(timer);
  }, [options.delay, options.enabled, options.value, saveNow]);

  return {
    status,
    valueRef,
    track,
    reset,
    saveNow,
  };
}
