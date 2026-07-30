import { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { Input } from '../../components/ui/Input';
import { Skeleton } from '../../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { processApi } from '../../services/process-api';
import type { ProcessSummary } from '../../types/process';
import './processes.css';

export function ProcessList() {
  const [items, setItems] = useState<ProcessSummary[]>([]);
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebouncedValue(query);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      setItems(await processApi.list());
    } catch {
      setError('Interview processes could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => void load(), [load]);

  const filtered = useMemo(() => {
    const normalized = debouncedQuery.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter((item) =>
      [item.title, item.company_name, item.target_role]
        .join(' ')
        .toLowerCase()
        .includes(normalized),
    );
  }, [debouncedQuery, items]);

  if (loading)
    return (
      <div className="processes__list" aria-label="Loading processes">
        <Skeleton height="12rem" />
        <Skeleton height="12rem" />
      </div>
    );
  if (error) return <ErrorState message={error} onRetry={() => void load()} />;

  return (
    <div className="processes">
      <div className="processes__toolbar">
        <Input
          className="processes__search"
          type="search"
          aria-label="Filter processes"
          placeholder="Filter processes…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <a className="ui-button ui-button--primary" href="/processes/new">
          <Icon name="plus" /> New process
        </a>
      </div>
      {filtered.length ? (
        <div className="processes__list">
          {filtered.map((item) => {
            const progress = item.stage_count
              ? (item.completed_stage_count / item.stage_count) * 100
              : 0;
            return (
              <a
                key={item.id}
                href={`/processes/details?id=${encodeURIComponent(item.id)}`}
                className="ui-card processes__card"
              >
                <div>
                  <h2>{item.title}</h2>
                  <p className="processes__meta">
                    {[item.company_name, item.target_role]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                </div>
                <div className="processes__progress">
                  <span>
                    {item.completed_stage_count} of {item.stage_count} stages
                  </span>
                  <div className="processes__progress-track" aria-hidden="true">
                    <div
                      className="processes__progress-value"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <small>{item.attempt_count} attempts</small>
                </div>
                <Badge>{item.status}</Badge>
              </a>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title={debouncedQuery ? 'No matching processes' : 'No processes yet'}
        >
          <p>
            {debouncedQuery
              ? 'Try a different role or company.'
              : 'Create a process to configure your interview stages.'}
          </p>
        </EmptyState>
      )}
    </div>
  );
}
