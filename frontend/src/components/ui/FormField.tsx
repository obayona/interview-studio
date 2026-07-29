import type { ReactNode } from 'react';

export function FormField({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  const messageId = `${htmlFor}-message`;
  return (
    <div className="ui-field">
      <label className="ui-field__label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {(error || hint) && (
        <p
          className={error ? 'ui-field__error' : 'ui-field__hint'}
          id={messageId}
        >
          {error ?? hint}
        </p>
      )}
    </div>
  );
}
