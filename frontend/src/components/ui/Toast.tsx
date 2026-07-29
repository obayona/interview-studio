import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { Icon } from './Icon';

type ToastItem = { id: number; message: string; tone: 'success' | 'error' };
type ToastContextValue = {
  showToast: (message: string, tone?: ToastItem['tone']) => void;
};
const ToastContext = createContext<ToastContextValue | null>(null);

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

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) throw new Error('useToast must be used inside ToastProvider');
  return value;
}
