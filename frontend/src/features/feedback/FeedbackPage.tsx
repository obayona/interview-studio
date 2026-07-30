import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { Spinner } from '../../components/ui/Spinner';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { ApiError } from '../../services/api-client';
import {
  interviewApi,
  type TranscriptMessage,
} from '../../services/interview-api';
import { reportApi } from '../../services/report-api';
import type {
  CompetencyScores,
  EvaluationReport,
  ProcessReport,
  SourcedText,
} from '../../types/report';
import './feedback.css';

const competencyLabels: Record<keyof CompetencyScores, string> = {
  communication: 'Communication',
  technical_knowledge: 'Technical knowledge',
  problem_solving: 'Problem solving',
  confidence: 'Confidence',
  answer_relevance: 'Answer relevance',
};

type PageState = 'loading' | 'evaluating' | 'empty' | 'error' | 'ready';

function ScoreOverview({
  score,
  competencies,
}: {
  score: number;
  competencies: CompetencyScores;
}) {
  return (
    <div className="feedback__overview">
      <Card className="feedback__score">
        <span>Overall performance</span>
        <strong>{score}</strong>
        <small>/ 100</small>
      </Card>
      <Card className="feedback__competencies">
        <h2>Competency breakdown</h2>
        {Object.entries(competencies).map(([key, value]) => (
          <div className="feedback__competency" key={key}>
            <div>
              <span>{competencyLabels[key as keyof CompetencyScores]}</span>
              <span>{value}/100</span>
            </div>
            <progress
              max="100"
              value={value}
              aria-label={competencyLabels[key as keyof CompetencyScores]}
            />
          </div>
        ))}
      </Card>
    </div>
  );
}

function AttemptFeedback({
  report,
  messages,
}: {
  report: EvaluationReport;
  messages: TranscriptMessage[];
}) {
  const observations = useMemo(
    () =>
      new Map(
        report.answer_observations.map((item) => [item.message_id, item]),
      ),
    [report.answer_observations],
  );
  return (
    <>
      <ScoreOverview
        score={report.overall_score}
        competencies={report.competencies}
      />
      <p className="feedback__summary">{report.summary}</p>
      <div className="feedback__grid">
        <Card>
          <h2>Strengths</h2>
          <ul>
            {report.strengths.map((item) => (
              <li key={item.title}>
                <strong>{item.title}</strong>
                <span>{item.detail}</span>
                {item.evidence.map((evidence) => (
                  <a
                    key={evidence.message_id}
                    href={`#message-${encodeURIComponent(evidence.message_id)}`}
                  >
                    View transcript evidence
                  </a>
                ))}
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2>Areas for improvement</h2>
          <ul>
            {report.improvements.map((item) => (
              <li key={item.title}>
                <strong>{item.title}</strong>
                <span>{item.detail}</span>
                {item.evidence.map((evidence) => (
                  <a
                    key={evidence.message_id}
                    href={`#message-${encodeURIComponent(evidence.message_id)}`}
                  >
                    View transcript evidence
                  </a>
                ))}
              </li>
            ))}
          </ul>
        </Card>
        <Card className="feedback__next">
          <h2>Recommended next steps</h2>
          <ul>
            {report.advice.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2>Study plan</h2>
          <ol>
            {[...report.study_plan]
              .sort((a, b) => a.priority - b.priority)
              .map((item) => (
                <li key={`${item.priority}-${item.topic}`}>
                  <strong>{item.topic}</strong>
                  <span>{item.action}</span>
                </li>
              ))}
          </ol>
        </Card>
      </div>
      <Card className="feedback__transcript">
        <h2>Evidence-linked transcript</h2>
        <ol>
          {messages.map((message) => {
            const observation = observations.get(message.id);
            return (
              <li
                id={`message-${message.id}`}
                key={message.id}
                className={observation ? 'is-observed' : ''}
              >
                <strong>
                  {message.role === 'user' ? 'You' : 'Interviewer'}
                </strong>
                <p>{message.text}</p>
                {observation && (
                  <aside>
                    <b>{observation.score}/100</b> {observation.observation}
                    <span>{observation.advice}</span>
                  </aside>
                )}
              </li>
            );
          })}
        </ol>
      </Card>
    </>
  );
}

function SourcedList({ items }: { items: SourcedText[] }) {
  return (
    <ul>
      {items.map((item) => (
        <li key={`${item.attempt_id}-${item.text}`}>
          <span>{item.text}</span>
          <small>
            {item.stage_type.replaceAll('_', ' ')} · Attempt{' '}
            {item.attempt_number}
          </small>
        </li>
      ))}
    </ul>
  );
}

function ProcessFeedbackView({ report }: { report: ProcessReport }) {
  return (
    <>
      <ScoreOverview
        score={report.overall_score}
        competencies={report.competencies}
      />
      <p className="feedback__coverage">
        {report.evaluated_stage_count} of {report.enabled_stage_count} enabled
        stages evaluated. The highest-scoring attempt from each evaluated stage
        is included.
      </p>
      <div className="feedback__grid">
        <Card>
          <h2>Consolidated strengths</h2>
          <SourcedList items={report.strengths} />
        </Card>
        <Card>
          <h2>Consolidated improvements</h2>
          <SourcedList items={report.improvements} />
        </Card>
        <Card className="feedback__next">
          <h2>Recommended next steps</h2>
          <SourcedList items={report.advice} />
        </Card>
        <Card>
          <h2>Study plan</h2>
          <SourcedList items={report.study_plan} />
        </Card>
      </div>
      <Card>
        <h2>Selected stage attempts</h2>
        <ul>
          {report.selected_reports.map((item) => (
            <li key={item.stage_id}>
              <a
                href={`/feedback?attempt=${encodeURIComponent(item.attempt_id)}&process=${encodeURIComponent(report.process_id)}`}
              >
                {item.stage_type.replaceAll('_', ' ')} · Attempt{' '}
                {item.attempt_number}
              </a>
              <strong>{item.overall_score}/100</strong>
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}

export function FeedbackPage() {
  const [state, setState] = useState<PageState>('loading');
  const [attemptReport, setAttemptReport] = useState<EvaluationReport>();
  const [processReport, setProcessReport] = useState<ProcessReport>();
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [error, setError] = useState('The feedback could not be loaded.');
  const params = useMemo(
    () =>
      new URLSearchParams(
        typeof window === 'undefined' ? '' : window.location.search,
      ),
    [],
  );
  const attemptId = params.get('attempt');
  const processId = params.get('process');
  const shouldEvaluate = params.get('evaluate') === '1';

  const load = useCallback(
    async (forceEvaluation = false) => {
      setError('The feedback could not be loaded.');
      if (attemptId) {
        setState('loading');
        try {
          const [report, history] = await Promise.all([
            reportApi.getAttempt(attemptId),
            interviewApi.history(attemptId),
          ]);
          setAttemptReport(report);
          setMessages(history.messages);
          setState('ready');
        } catch (requestError) {
          if (
            requestError instanceof ApiError &&
            requestError.code === 'report_not_found'
          ) {
            if (shouldEvaluate || forceEvaluation) {
              setState('evaluating');
              try {
                const [report, history] = await Promise.all([
                  reportApi.evaluate(attemptId),
                  interviewApi.history(attemptId),
                ]);
                setAttemptReport(report);
                setMessages(history.messages);
                setState('ready');
              } catch (evaluationError) {
                setError(
                  evaluationError instanceof Error
                    ? evaluationError.message
                    : 'Evaluation failed.',
                );
                setState('error');
              }
            } else setState('empty');
          } else {
            setError(
              requestError instanceof Error
                ? requestError.message
                : 'Feedback could not be loaded.',
            );
            setState('error');
          }
        }
        return;
      }
      if (processId) {
        setState('loading');
        try {
          setProcessReport(await reportApi.getProcess(processId));
          setState('ready');
        } catch (requestError) {
          if (
            requestError instanceof ApiError &&
            requestError.code === 'process_report_not_found'
          )
            setState('empty');
          else {
            setError(
              requestError instanceof Error
                ? requestError.message
                : 'Process feedback could not be loaded.',
            );
            setState('error');
          }
        }
        return;
      }
      setError('No interview attempt or process was selected.');
      setState('error');
    },
    [attemptId, processId, shouldEvaluate],
  );

  useEffect(() => void load(), [load]);

  const backHref = processId
    ? `/processes/details?id=${encodeURIComponent(processId)}`
    : '/processes';
  return (
    <section className="feedback">
      <a className="page__back-link" href={backHref}>
        <Icon name="arrowLeft" /> Back to process
      </a>
      <header>
        <div>
          <span>Performance feedback</span>
          <h1>{processReport?.process_title ?? 'Interview report'}</h1>
        </div>
      </header>
      {(state === 'loading' || state === 'evaluating') && (
        <div className="feedback__loading" role="status">
          <Spinner />
          <h2>
            {state === 'evaluating'
              ? 'Evaluating your interview…'
              : 'Loading feedback…'}
          </h2>
          <p>
            {state === 'evaluating'
              ? 'Reviewing each answer and preparing an evidence-based study plan. Keep this page open.'
              : 'Retrieving the completed report.'}
          </p>
        </div>
      )}
      {state === 'error' && (
        <ErrorState message={error} onRetry={() => void load(true)} />
      )}
      {state === 'empty' && (
        <EmptyState title="No feedback yet">
          <p>
            {attemptId
              ? 'This completed attempt is ready to evaluate.'
              : 'Evaluate completed attempts to build process feedback.'}
          </p>
          {attemptId && (
            <Button variant="primary" onClick={() => void load(true)}>
              Evaluate interview
            </Button>
          )}
        </EmptyState>
      )}
      {state === 'ready' && attemptReport && (
        <AttemptFeedback report={attemptReport} messages={messages} />
      )}
      {state === 'ready' && processReport && (
        <ProcessFeedbackView report={processReport} />
      )}
    </section>
  );
}
