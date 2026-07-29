import type { ReactNode } from 'react';
import { Icon } from './Icon';

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="ui-state">
      <div>
        <div className="ui-state__icon">
          <Icon name="info" />
        </div>
        <h3 className="ui-state__title">{title}</h3>
        <div className="ui-state__copy">{children}</div>
      </div>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="ui-state ui-state--error" role="alert">
      <div>
        <div className="ui-state__icon">
          <Icon name="error" />
        </div>
        <h3 className="ui-state__title">Something went wrong</h3>
        <p className="ui-state__copy">{message}</p>
        {onRetry && (
          <button className="ui-button" onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
