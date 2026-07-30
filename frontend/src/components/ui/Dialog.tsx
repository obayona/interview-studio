import { useEffect, useRef, type ComponentPropsWithoutRef } from 'react';

type DialogProps = Omit<ComponentPropsWithoutRef<'dialog'>, 'open'> & {
  open: boolean;
};

export function Dialog({
  open,
  children,
  className = '',
  ...properties
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (open && !ref.current?.open) ref.current?.showModal();
    if (!open && ref.current?.open) ref.current.close();
  }, [open]);

  return (
    <dialog
      {...properties}
      className={`ui-dialog ${className}`.trim()}
      ref={ref}
    >
      {children}
    </dialog>
  );
}
