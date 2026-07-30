import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { Icon } from './Icon';
import { ToastContext, type ToastTone } from './toast-context';

type ToastItem = { id: number; message: string; tone: ToastTone };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const showToast = useCallback(
    (message: string, tone: ToastItem['tone'] = 'success') => {
      const id = Date.now();
      setItems((current) => [...current, { id, message, tone }]);
      window.setTimeout(
        () => setItems((current) => current.filter((item) => item.id !== id)),
        4500,
      );
    },
    [],
  );
  const value = useMemo(() => ({ showToast }), [showToast]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="ui-toast-region" aria-live="polite">
        {items.map((item) => (
          <div className="ui-toast" key={item.id}>
            <Icon name={item.tone === 'success' ? 'check' : 'error'} />
            <span>{item.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export { useToast } from './toast-context';
