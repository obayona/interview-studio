import { useEffect, useRef, type ReactNode } from 'react';
import { Button } from './Button';

export function Dialog({
  open,
  title,
  children,
  onClose,
  onConfirm,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  onConfirm?: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (open && !ref.current?.open) ref.current?.showModal();
    if (!open && ref.current?.open) ref.current.close();
  }, [open]);
  return (
    <dialog className="ui-dialog" ref={ref} onClose={onClose}>
      <div className="ui-dialog__content">
        <h2>{title}</h2>
        {children}
        <div className="ui-dialog__actions">
          <Button onClick={onClose}>Cancel</Button>
          {onConfirm && (
            <Button variant="primary" onClick={onConfirm}>
              Confirm
            </Button>
          )}
        </div>
      </div>
    </dialog>
  );
}
