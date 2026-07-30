import { useCallback, useEffect, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Dialog } from '../../components/ui/Dialog';
import { Icon } from '../../components/ui/Icon';
import { Skeleton } from '../../components/ui/Skeleton';
import { ErrorState } from '../../components/ui/States';
import { ToastProvider, useToast } from '../../components/ui/Toast';
import { processApi } from '../../services/process-api';
import type { AttemptSummary, InterviewProcess } from '../../types/process';
import { stageLabels } from './defaults';
import './processes.css';

const attemptStatusLabels: Record<string, string> = {
  ready: 'Ready to start',
  in_progress: 'In progress',
  paused: 'Paused',
  completed: 'Completed',
};

const stageStatusLabels: Record<string, string> = {
  not_started: 'Not started',
  in_progress: 'In progress',
  completed: 'Completed',
  skipped: 'Skipped',
};

function ProcessDetailContent() {
  const { showToast } = useToast();
  const [process, setProcess] = useState<InterviewProcess>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [startingStage, setStartingStage] = useState<string>();
  const [attemptToDelete, setAttemptToDelete] = useState<AttemptSummary>();
  const [deletingAttempt, setDeletingAttempt] = useState(false);
  const [processId, setProcessId] = useState<string | null>();

  useEffect(() => {
    setProcessId(new URLSearchParams(window.location.search).get('id'));
  }, []);

  const load = useCallback(async () => {
    if (processId === undefined) return;
    if (!processId) {
      setError('No interview process was selected.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      setProcess(await processApi.get(processId));
    } catch {
      setError('Interview process could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [processId]);

  useEffect(() => void load(), [load]);

  const start = async (stageId: string) => {
    if (!processId) return;
    setStartingStage(stageId);
    try {
      const attempt = await processApi.startAttempt(processId, stageId);
      window.location.href =
        `/interview?attempt=${encodeURIComponent(attempt.id)}` +
        `&process=${encodeURIComponent(processId)}`;
    } catch {
      showToast('Interview attempt could not be created.', 'error');
      setStartingStage(undefined);
    }
  };

  const remove = async () => {
    if (!processId) return;
    setDeleting(true);
    try {
      await processApi.remove(processId);
      window.location.href = '/processes';
    } catch {
      showToast('Process could not be deleted.', 'error');
      setDeleting(false);
    }
  };

  const removeAttempt = async () => {
    if (!attemptToDelete) return;
    setDeletingAttempt(true);
    try {
      await processApi.deleteAttempt(attemptToDelete.id);
      setAttemptToDelete(undefined);
      await load();
      showToast(
        `Attempt ${attemptToDelete.attempt_number} deleted.`,
        'success',
      );
    } catch {
      showToast('Interview attempt could not be deleted.', 'error');
    } finally {
      setDeletingAttempt(false);
    }
  };

  if (loading) return <Skeleton height="50rem" />;
  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!process) return null;

  return (
    <div className="processes">
      <div className="processes__detail-header">
        <div>
          <Badge>{process.status}</Badge>
          <h2>{process.title}</h2>
          <p className="processes__meta">
            {[process.company_name, process.target_role]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <div className="processes__actions">
          <a
            className="ui-button"
            href={`/processes/edit?id=${encodeURIComponent(process.id)}`}
          >
            Edit process
          </a>
          <Button variant="danger" onClick={() => setDeleteOpen(true)}>
            <Icon name="trash" /> Delete
          </Button>
        </div>
      </div>

      <div className="processes__detail-layout">
        <div className="processes__detail-main">
          {process.stages.map((stage) => (
            <Card className="processes__stage" key={stage.id}>
              <div className="processes__stage-heading">
                <div>
                  <h2>
                    Stage {stage.position + 1}: {stageLabels[stage.stage_type]}
                  </h2>
                  <p className="processes__meta">
                    {stage.configuration.difficulty} ·{' '}
                    {stage.configuration.interviewer_profile.replaceAll(
                      '_',
                      ' ',
                    )}{' '}
                    · {stage.configuration.limits.max_duration_minutes} minutes
                  </p>
                </div>
                <Badge>
                  {stageStatusLabels[
                    stage.enabled ? stage.status : 'skipped'
                  ] ?? stage.status.replaceAll('_', ' ')}
                </Badge>
              </div>
              {stage.configuration.user_instructions && (
                <p>{stage.configuration.user_instructions}</p>
              )}
              {stage.configuration.topics.length > 0 && (
                <p className="processes__muted">
                  Topics: {stage.configuration.topics.join(', ')}
                </p>
              )}
              <Button
                variant="primary"
                disabled={!stage.enabled || startingStage === stage.id}
                onClick={() => void start(stage.id)}
              >
                {startingStage === stage.id
                  ? 'Preparing…'
                  : stage.attempts.length
                    ? 'Repeat interview'
                    : 'Start interview'}
              </Button>
              {stage.attempts.length > 0 && (
                <ul
                  className="processes__attempts"
                  aria-label="Attempt history"
                >
                  {stage.attempts.map((attempt) => (
                    <li className="processes__attempt" key={attempt.id}>
                      <div className="processes__attempt-summary">
                        <strong>Attempt {attempt.attempt_number}</strong>
                        <span>
                          {new Date(attempt.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="processes__attempt-actions">
                        <Badge>
                          {attemptStatusLabels[attempt.status] ??
                            attempt.status.replaceAll('_', ' ')}
                        </Badge>
                        <a
                          className="ui-button ui-button--icon"
                          href={`/interview?attempt=${encodeURIComponent(
                            attempt.id,
                          )}&process=${encodeURIComponent(process.id)}`}
                          aria-label={
                            attempt.status === 'completed'
                              ? 'View attempt'
                              : attempt.status === 'ready'
                                ? 'Start attempt'
                                : 'Resume attempt'
                          }
                          title={
                            attempt.status === 'completed'
                              ? 'View attempt'
                              : attempt.status === 'ready'
                                ? 'Start attempt'
                                : 'Resume attempt'
                          }
                        >
                          <Icon
                            name={
                              attempt.status === 'completed'
                                ? 'view'
                                : attempt.status === 'ready'
                                  ? 'play'
                                  : 'resume'
                            }
                          />
                        </a>
                        <Button
                          variant="danger"
                          aria-label={`Delete attempt ${attempt.attempt_number}`}
                          title={`Delete attempt ${attempt.attempt_number}`}
                          onClick={() => setAttemptToDelete(attempt)}
                        >
                          <Icon name="trash" />
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>
        <aside className="processes__stage-list">
          <Card>
            <h2>Job context</h2>
            <p className="processes__preview">{process.job_description}</p>
          </Card>
          {process.company_info && (
            <Card>
              <h2>Company context</h2>
              <p className="processes__preview">{process.company_info}</p>
            </Card>
          )}
          <Card>
            <h2>Feedback</h2>
            <p className="processes__muted">
              Feedback and interview scores will appear here after evaluation is
              introduced in Phase 8.
            </p>
          </Card>
        </aside>
      </div>

      <Dialog
        open={deleteOpen}
        onClose={() => {
          if (!deleting) setDeleteOpen(false);
        }}
      >
        <div className="ui-dialog__content">
          <h2>Delete interview process?</h2>
          <p>
            This permanently deletes its stages, attempts, transcripts, and
            future feedback.
          </p>
          <div className="ui-dialog__actions">
            <Button disabled={deleting} onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={deleting}
              onClick={() => void remove()}
            >
              {deleting ? 'Deleting…' : 'Delete process'}
            </Button>
          </div>
        </div>
      </Dialog>

      <Dialog
        open={Boolean(attemptToDelete)}
        onClose={() => {
          if (!deletingAttempt) setAttemptToDelete(undefined);
        }}
      >
        <div className="ui-dialog__content">
          <h2>Delete interview attempt?</h2>
          <p>
            This permanently deletes attempt {attemptToDelete?.attempt_number},
            including its transcript and checkpoint.
          </p>
          <div className="ui-dialog__actions">
            <Button
              disabled={deletingAttempt}
              onClick={() => setAttemptToDelete(undefined)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={deletingAttempt}
              onClick={() => void removeAttempt()}
            >
              {deletingAttempt ? 'Deleting…' : 'Delete attempt'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

export function ProcessDetail() {
  return (
    <ToastProvider>
      <ProcessDetailContent />
    </ToastProvider>
  );
}
