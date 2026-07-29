export function Skeleton({ height = '2rem' }: { height?: string }) {
  return <div className="ui-skeleton" style={{ height }} aria-hidden="true" />;
}
