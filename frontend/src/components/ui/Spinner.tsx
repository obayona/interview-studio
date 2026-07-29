import { Icon } from './Icon';

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <span className="ui-spinner" role="status">
      <Icon name="spinner" spin />
      <span className="sr-only">{label}</span>
    </span>
  );
}
