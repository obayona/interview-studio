import { useCallback, useEffect, useMemo, useState } from 'react';
import { Icon, type IconName } from '../../components/ui/Icon';
import { Skeleton } from '../../components/ui/Skeleton';
import { ErrorState } from '../../components/ui/States';
import { dashboardApi } from '../../services/dashboard-api';
import type {
  DashboardActivity,
  DashboardData,
  ScoreTrendPoint,
} from '../../types/dashboard';
import './dashboard.css';

const statusLabels: Record<string, string> = {
  ready: 'Ready to start',
  in_progress: 'In progress',
  paused: 'Paused',
  completed: 'Completed',
};

const stageLabels: Record<string, string> = {
  behavioral: 'Behavioral',
  technical: 'Technical',
  system_design: 'System design',
  coding: 'Coding',
};

function StatCard({
  icon,
  label,
  value,
  detail,
}: {
  icon: IconName;
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <article className="ui-card dashboard__stat">
      <span className="dashboard__stat-icon" aria-hidden="true">
        <Icon name={icon} />
      </span>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function TrendChart({ points }: { points: ScoreTrendPoint[] }) {
  if (!points.length)
    return (
      <p className="dashboard__empty-copy">
        Evaluated interviews will build your score trend.
      </p>
    );
  const coordinates = points
    .map((point, index) => {
      const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
      return `${x},${100 - point.score}`;
    })
    .join(' ');
  return (
    <div className="dashboard__chart">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Score trend from ${points[0].score} to ${points.at(-1)?.score}`}
      >
        <polyline points={coordinates} />
      </svg>
      <div className="dashboard__chart-labels">
        <span>{points[0].score}</span>
        <span>{points.at(-1)?.score}</span>
      </div>
    </div>
  );
}

function ActivityItem({ item }: { item: DashboardActivity }) {
  const href =
    item.status === 'completed' && item.score !== null
      ? `/feedback?attempt=${encodeURIComponent(item.attempt_id)}&process=${encodeURIComponent(item.process_id)}`
      : `/processes/details?id=${encodeURIComponent(item.process_id)}`;
  return (
    <li>
      <a className="dashboard__activity-link" href={href}>
        <span className="dashboard__activity-icon" aria-hidden="true">
          <Icon name={item.score === null ? 'interview' : 'report'} />
        </span>
        <span>
          <strong>{item.process_title}</strong>
          <small>
            {stageLabels[item.stage_type] ?? item.stage_type} · Attempt{' '}
            {item.attempt_number} · {formatDate(item.occurred_at)}
          </small>
        </span>
        <span className="dashboard__activity-status">
          {item.score === null
            ? (statusLabels[item.status] ?? item.status)
            : `${item.score}/100`}
        </span>
      </a>
    </li>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year:
      new Date(value).getFullYear() === new Date().getFullYear()
        ? undefined
        : 'numeric',
  }).format(new Date(value));
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData>();
  const [error, setError] = useState<string>();

  const load = useCallback(async () => {
    setError(undefined);
    try {
      setData(await dashboardApi.get());
    } catch {
      setError('Your dashboard could not be loaded.');
    }
  }, []);

  useEffect(() => void load(), [load]);

  const onboarding = useMemo(
    () =>
      data
        ? [
            {
              complete: data.onboarding.settings_configured,
              icon: 'settings' as const,
              title: 'Configure AI',
              copy: 'Connect OpenAI to enable interviews and feedback.',
              href: '/settings',
              action: 'Open settings',
            },
            {
              complete: data.onboarding.profile_completed,
              icon: 'user' as const,
              title: 'Complete your profile',
              copy: 'Add your experience and skills for tailored questions.',
              href: '/profile',
              action: 'Open profile',
            },
            {
              complete: data.onboarding.process_created,
              icon: 'briefcase' as const,
              title: 'Create a process',
              copy: 'Define the role, company, and interview stages.',
              href: '/processes/new',
              action: 'New process',
            },
            {
              complete: data.onboarding.interview_started,
              icon: 'interview' as const,
              title: 'Practice an interview',
              copy: 'Start an attempt from one of your configured stages.',
              href: '/processes',
              action: 'View processes',
            },
          ]
        : [],
    [data],
  );

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!data)
    return (
      <div className="dashboard" aria-label="Loading dashboard">
        <div className="dashboard__stats">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} height="14rem" />
          ))}
        </div>
        <Skeleton height="34rem" />
      </div>
    );

  return (
    <div className="dashboard">
      <header className="dashboard__intro">
        <div>
          <p className="dashboard__eyebrow">Your practice overview</p>
          <h1>Dashboard</h1>
          <p className="dashboard__intro-copy">
            Track interview activity and turn feedback into focused practice.
          </p>
        </div>
        <a className="ui-button ui-button--primary" href="/processes">
          <Icon name="play" /> Start interview
        </a>
      </header>

      <section className="dashboard__stats" aria-label="Interview statistics">
        <StatCard
          icon="check"
          label="Completed interviews"
          value={data.stats.completed_attempt_count}
          detail={`${data.stats.attempt_count} total attempts`}
        />
        <StatCard
          icon="report"
          label="Average score"
          value={
            data.stats.average_score === null
              ? '—'
              : `${data.stats.average_score}`
          }
          detail={`${data.stats.evaluated_attempt_count} evaluated`}
        />
        <StatCard
          icon="arrowUp"
          label="Score range"
          value={
            data.stats.minimum_score === null
              ? '—'
              : `${data.stats.minimum_score}–${data.stats.maximum_score}`
          }
          detail="Minimum to maximum"
        />
        <StatCard
          icon="briefcase"
          label="Active processes"
          value={data.stats.active_process_count}
          detail={`${data.stats.process_count} total processes`}
        />
      </section>

      {onboarding.some((item) => !item.complete) && (
        <section
          className="dashboard__section"
          aria-labelledby="getting-started"
        >
          <div className="dashboard__section-heading">
            <div>
              <p className="dashboard__eyebrow">First run</p>
              <h2 id="getting-started">Get started</h2>
            </div>
            <span>
              {onboarding.filter((item) => item.complete).length} of{' '}
              {onboarding.length} complete
            </span>
          </div>
          <div className="dashboard__guidance">
            {onboarding.map((item, index) => (
              <article
                className={`ui-card dashboard__guide${item.complete ? ' dashboard__guide--complete' : ''}`}
                key={item.title}
              >
                <span className="dashboard__guide-number">
                  {item.complete ? <Icon name="check" /> : index + 1}
                </span>
                <Icon name={item.icon} />
                <h3>{item.title}</h3>
                <p>{item.copy}</p>
                <a href={item.href}>
                  {item.complete ? 'Review' : item.action}{' '}
                  <Icon name="arrowRight" />
                </a>
              </article>
            ))}
          </div>
        </section>
      )}

      <div className="dashboard__grid">
        <section
          className="ui-card dashboard__section"
          aria-labelledby="score-trend"
        >
          <div className="dashboard__section-heading">
            <h2 id="score-trend">Score trend</h2>
            <span>{data.score_trend.length} reports</span>
          </div>
          <TrendChart points={data.score_trend} />
        </section>
        <section
          className="ui-card dashboard__section"
          aria-labelledby="feedback-topics"
        >
          <div className="dashboard__section-heading">
            <h2 id="feedback-topics">Feedback themes</h2>
          </div>
          <div className="dashboard__topics">
            <div>
              <h3>Strengths</h3>
              {data.strengths.length ? (
                <ul>
                  {data.strengths.map((item) => (
                    <li key={item.label}>
                      <span>{item.label}</span>
                      <strong>{item.count}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No evaluated strengths yet.</p>
              )}
            </div>
            <div>
              <h3>Focus areas</h3>
              {data.weaknesses.length ? (
                <ul>
                  {data.weaknesses.map((item) => (
                    <li key={item.label}>
                      <span>{item.label}</span>
                      <strong>{item.count}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No focus areas yet.</p>
              )}
            </div>
          </div>
        </section>
      </div>

      <section
        className="ui-card dashboard__section"
        aria-labelledby="recent-activity"
      >
        <div className="dashboard__section-heading">
          <h2 id="recent-activity">Recent activity</h2>
          <a href="/processes">View processes</a>
        </div>
        {data.recent_activity.length ? (
          <ul className="dashboard__activity">
            {data.recent_activity.map((item) => (
              <ActivityItem item={item} key={item.attempt_id} />
            ))}
          </ul>
        ) : (
          <p className="dashboard__empty-copy">
            Your interview attempts will appear here.
          </p>
        )}
      </section>
    </div>
  );
}
